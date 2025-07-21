# repomind.py

import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Tuple

EXCLUDE_PATTERNS = ["test", "__init__", "setup", "example"]

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
    summary = {"kept": {}, "pruned": []}

    for root, _, files in os.walk(repo_path):
        for file in files:
            if not file.endswith(".py"):
                continue
            full_path = Path(root) / file

            if should_prune(full_path):
                summary["pruned"].append(str(full_path))
                continue

            funcs, calls = extract_functions_and_calls(full_path)
            if not funcs:
                summary["pruned"].append(str(full_path))
                continue

            summary["kept"][str(full_path)] = {
                "functions": funcs,
                "calls": calls,
                "num_functions": len(funcs),
                "num_calls": len(calls)
            }

    return summary

def save_summary(summary: Dict, out_path: Path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=str, help="Path to the local repo to explore")
    parser.add_argument("--out", type=str, default="repomind_summary.json")
    args = parser.parse_args()

    repo_path = Path(args.repo)
    summary = explore_repo(repo_path)
    save_summary(summary, Path(args.out))

    print(f"✅ Analysis complete. Saved to {args.out}")

if __name__ == "__main__":
    main()
