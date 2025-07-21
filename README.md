# Repomind

`repomind.py` is a utility script that scans a Python code base and creates a JSON summary of the functions defined and the functions called in each file.

## Features

- Recursively walks a target repository path.
- Ignores files whose names contain any of the words `test`, `__init__`, `setup`, or `example`.
- For each kept Python file, lists all function definitions and the functions they call.
- Records the number of functions and calls for quick inspection.
- Saves the gathered information to a JSON file (defaults to `repomind_summary.json`).

## Usage

```bash
python repomind.py path/to/repo [--out OUTPUT_FILE]
```

`OUTPUT_FILE` is optional and controls where the JSON summary is written.

The script prints a success message when analysis is complete and the summary file has been saved.
