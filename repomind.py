# repomind.py

import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

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

def explore_repo(repo_path: Path) -> Dict:
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
    return summary

def save_summary(summary: Dict, out_path: Path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


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
    args = parser.parse_args()

    repo_path = Path(args.repo)
    summary = explore_repo(repo_path)
    save_summary(summary, Path(args.out))

    # Update memory history alongside the repo
    memory_path = repo_path / "repomind_memory.json"
    manager = MemoryManager(memory_path)
    manager.add_summary(summary)
    manager.save()

    print(f"✅ Analysis complete. Saved to {args.out}")

if __name__ == "__main__":
    main()
