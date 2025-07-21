import ast
from pathlib import Path
from typing import List

"""Docstring Enhancer utility.

This lightweight script reports functions and classes missing docstrings. It's
designed to grow into a full docstring injection tool.

✨ **What It's Missing (But Ready For)**
This script is meant to be extended — here's what we can add next:

Feature           Description
--write mode      Actually injects generated docstrings via Codex
Codex integration Sends context + function body to Codex to generate summaries
.patched.py output Saves a version of the file with proposed docstrings, for safe review
Markdown export   Optionally outputs function summaries to `docs/`

✅ **You're on the Right Path**
This is Step 1 of a 3‑step enhancer:

🔎 Detect what's missing → done
✍️ Prompt Codex to generate summaries → next
🧪 Apply or preview safely → coming
"""


def find_missing_docstrings(path: Path) -> List[str]:
    """Return a list of functions or classes without docstrings."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    missing = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if ast.get_docstring(node) is None:
                missing.append(node.name)
    return missing


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Report functions/classes missing docstrings")
    parser.add_argument("file", type=str, help="Python file to analyze")
    args = parser.parse_args()

    target = Path(args.file)
    if not target.exists():
        print(f"{target} does not exist")
        return

    missing = find_missing_docstrings(target)
    if not missing:
        print("All functions and classes have docstrings.")
    else:
        print("Missing docstrings:")
        for name in missing:
            print(f"- {name}")


if __name__ == "__main__":
    main()
