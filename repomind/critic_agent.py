import json
from pathlib import Path
from typing import Dict, List


def review_summary_data(data: Dict) -> List[str]:

    call_counts = data.get("call_counts", {})
    kept = data.get("kept", {})
    pruned = data.get("pruned", [])

    issues = []
    for file_path in pruned:
        info = kept.get(file_path)
        if info:
            continue
        # If any of its functions are referenced, raise an issue
        # we don't know functions because pruned file info is not stored; skip

    # Look for functions referenced but belonging to pruned files
    for func, count in call_counts.items():
        found = False
        for k, info in kept.items():
            if func in info.get("functions", []):
                found = True
                break
        if not found and count >= 1:
            issues.append(f"Function '{func}' is called {count} times but its definition was not kept.")

    return issues


def review_summary(summary_path: Path) -> None:
    data: Dict = json.loads(summary_path.read_text(encoding="utf-8"))
    issues = review_summary_data(data)

    if not issues:
        print("No obvious issues detected by critic agent.")
    else:
        print("Critic Agent Findings:")
        for issue in issues:
            print(f"- {issue}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Review repomind summary for possible issues")
    parser.add_argument("summary", type=str, help="Path to summary JSON file")
    args = parser.parse_args()

    review_summary(Path(args.summary))
