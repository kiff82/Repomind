# repomind.py

import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Iterable
import subprocess
import re

EXCLUDE_PATTERNS = ["test", "__init__", "setup", "example"]
# If a file's functions are called this many times across the project, keep it
# even if it would normally be pruned.
CALL_COUNT_THRESHOLD = 3

# Optional file that can be supplied alongside the repo to provide additional
# context for follow-up agents. If present, it will be embedded in the summary
# JSON output under the key ``prompt_context``.
def load_prompt_context(repo_path: Path) -> Optional[str]:
    context_file = repo_path / "prompt_context.txt"
    if context_file.exists():
        try:
            return context_file.read_text(encoding="utf-8")
        except OSError:
            return None
    return None

class FunctionCallVisitor(ast.NodeVisitor):
    def __init__(self):
        self.calls = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.append(node.func.attr)
        self.generic_visit(node)

def extract_functions_and_calls(filepath: Path) -> Tuple[List[str], List[str]]:
    with open(filepath, "r", encoding="utf-8") as file:
        try:
            tree = ast.parse(file.read())
        except SyntaxError:
            return [], []

    functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    visitor = FunctionCallVisitor()
    visitor.visit(tree)
    return functions, visitor.calls

def should_prune(filepath: Path) -> bool:
    name = filepath.name.lower()
    return any(pattern in name for pattern in EXCLUDE_PATTERNS)

def explore_repo(repo_path: Path) -> Tuple[Dict, Dict[str, Dict[str, List[str]]]]:
    """Walk the repository and build a summary with depth-aware pruning."""
    summary: Dict[str, Dict] = {
        "kept": {},
        "pruned": [],
        "call_counts": {},
        "prompt_context": load_prompt_context(repo_path),
    }

    file_info: Dict[str, Dict[str, List[str]]] = {}

    for root, _, files in os.walk(repo_path):
        for file in files:
            if not file.endswith(".py"):
                continue
            full_path = Path(root) / file
            if should_prune(full_path):
                summary["pruned"].append(str(full_path))
                continue

            funcs, calls = extract_functions_and_calls(full_path)
            file_info[str(full_path)] = {"functions": funcs, "calls": calls}

    # Compute how often each function is called across the project
    function_call_counts: Dict[str, int] = {}
    for data in file_info.values():
        for call in data["calls"]:
            function_call_counts[call] = function_call_counts.get(call, 0) + 1

    # Decide to keep or prune files based on depth-aware usage
    for fpath, data in file_info.items():
        call_count = sum(function_call_counts.get(func, 0) for func in data["functions"])
        data.update({
            "num_functions": len(data["functions"]),
            "num_calls": len(data["calls"]),
            "total_call_count": call_count,
        })

        if data["functions"] or call_count >= CALL_COUNT_THRESHOLD:
            summary["kept"][fpath] = data
        else:
            summary["pruned"].append(fpath)

    summary["call_counts"] = function_call_counts
    return summary, file_info

def save_summary(summary: Dict, out_path: Path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def apply_critic_feedback(summary: Dict, file_info: Dict[str, Dict[str, List[str]]]) -> None:
    """Use the critic agent to find missing functions and re-include their files."""
    from repomind.critic_agent import review_summary_data

    issues = review_summary_data(summary)
    if not issues:
        return

    missing_funcs = []
    for issue in issues:
        m = re.search(r"Function '([^']+)'", issue)
        if m:
            missing_funcs.append(m.group(1))

    readded = []
    for func in missing_funcs:
        for path, info in file_info.items():
            if func in info.get("functions", []):
                if path not in summary["kept"]:
                    summary["kept"][path] = info
                    if path in summary.get("pruned", []):
                        summary["pruned"].remove(path)
                    readded.append(path)
                break

    if readded:
        print("\n🔁 Critic feedback re-included files:")
        for p in readded:
            print(f" - {p}")


def build_call_graph(file_info: Dict[str, Dict[str, List[str]]], dot_path: Path, png_path: Optional[Path] = None) -> None:
    """Generate a simple file-level call graph in DOT format and optionally PNG."""
    lines = ["digraph G {"]
    files = {os.path.basename(p): p for p in file_info.keys()}
    for name in files:
        lines.append(f'"{name}" [shape=box];')

    edges = set()
    for src_path, data in file_info.items():
        src_name = os.path.basename(src_path)
        for call in data.get("calls", []):
            for dst_path, dst_data in file_info.items():
                if call in dst_data.get("functions", []) and src_path != dst_path:
                    dst_name = os.path.basename(dst_path)
                    edges.add((src_name, dst_name))

    for a, b in edges:
        lines.append(f'"{a}" -> "{b}";')
    lines.append("}")

    dot_path.write_text("\n".join(lines), encoding="utf-8")

    if png_path:
        try:
            subprocess.run(["dot", "-Tpng", str(dot_path), "-o", str(png_path)], check=False)
        except FileNotFoundError:
            pass


def generate_summary_paragraph(summary: Dict) -> str:
    """Return a short paragraph summarizing the repo."""
    kept = summary.get("kept", {})
    num_files = len(kept)
    total_funcs = sum(len(info.get("functions", [])) for info in kept.values())
    file_names = ", ".join(os.path.basename(f) for f in list(kept.keys())[:5])

    base = (
        f"The repository contains {num_files} important Python files with "
        f"{total_funcs} functions. Notable modules include {file_names}."
    )

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            import openai

            openai.api_key = api_key
            prompt = base + " Summarize the structure and purpose of this repository in one paragraph."
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return resp.choices[0].message["content"].strip()
        except Exception:
            pass
    return base


def report_structural_drift(old: Dict, new: Dict) -> None:
    """Compare two summaries and print messages about increased usage."""
    old_counts = old.get("call_counts", {})
    new_counts = new.get("call_counts", {})

    messages: List[str] = []
    for func, new_count in new_counts.items():
        old_count = old_counts.get(func, 0)
        if new_count > old_count:
            # Check if func is retained
            retained = any(func in info.get("functions", []) for info in new.get("kept", {}).values())
            if not retained:
                messages.append(
                    f"Function {func} is used more now, but still not retained."
                )

    if messages:
        print("\n🧠 Live Diff Awareness:")
        for m in messages:
            print(f"- {m}")


class MemoryManager:
    """Persist and optionally compress previous summaries."""

    def __init__(self, path: Path, max_entries: int = 5) -> None:
        self.path = path
        self.max_entries = max_entries
        self.history = self._load_history()

    def _load_history(self) -> List[Dict]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _compress_summary(self, summary: Dict) -> Dict:
        return {
            "kept_files": len(summary.get("kept", {})),
            "pruned_files": len(summary.get("pruned", [])),
        }

    def add_summary(self, summary: Dict) -> None:
        self.history.append(summary)
        if len(self.history) > self.max_entries:
            oldest = self.history.pop(0)
            self.history.insert(0, self._compress_summary(oldest))

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.history[-self.max_entries:], f, indent=2)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=str, help="Path to the local repo to explore")
    parser.add_argument("--out", type=str, default="repomind_summary.json")
    parser.add_argument("--callgraph", type=str, default=None, help="Optional path to write callgraph DOT file")
    parser.add_argument("--diagram", type=str, default=None, help="Optional path to write callgraph diagram PNG")
    parser.add_argument("--summary-text", type=str, default=None, help="Optional path to write repo summary paragraph")
    args = parser.parse_args()

    repo_path = Path(args.repo)
    summary, file_info = explore_repo(repo_path)

    # Apply feedback from critic agent to re-include missed files
    apply_critic_feedback(summary, file_info)

    save_summary(summary, Path(args.out))

    if args.callgraph:
        build_call_graph(file_info, Path(args.callgraph), Path(args.diagram) if args.diagram else None)

    if args.summary_text:
        paragraph = generate_summary_paragraph(summary)
        Path(args.summary_text).write_text(paragraph, encoding="utf-8")

    # Update memory history alongside the repo
    memory_path = repo_path / "repomind_memory.json"
    manager = MemoryManager(memory_path)
    previous = manager.history[-1] if manager.history else None
    manager.add_summary(summary)
    manager.save()

    if previous:
        report_structural_drift(previous, summary)

    print(f"✅ Analysis complete. Saved to {args.out}")

if __name__ == "__main__":
    main()
