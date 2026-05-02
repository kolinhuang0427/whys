"""
Function/anchor detection from source code.
Language-agnostic parser that identifies function definitions and line ranges.
"""

import re
from pathlib import Path
from typing import Optional


# Function definition patterns by extension
DEF_PATTERNS = {
    ".py": [
        re.compile(r"^(\s*)(def\s+(\w+)\s*\([^)]*\)\s*:)"),
        re.compile(r"^(\s*)(class\s+(\w+)(\s*\([^)]*\))?\s*:)"),
    ],
    ".js": [
        re.compile(r"^(\s*)(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("),
        re.compile(r"^(\s*)(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("),
        re.compile(r"^(\s*)(?:export\s+)?(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{"),
        re.compile(r"^(\s*)class\s+(\w+)"),
    ],
    ".ts": [
        re.compile(r"^(\s*)(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("),
        re.compile(r"^(\s*)(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("),
        re.compile(r"^(\s*)(?:export\s+)?(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{"),
        re.compile(r"^(\s*)class\s+(\w+)"),
    ],
    ".jsx": [
        re.compile(r"^(\s*)(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("),
        re.compile(r"^(\s*)class\s+(\w+)"),
    ],
    ".tsx": [
        re.compile(r"^(\s*)(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("),
        re.compile(r"^(\s*)class\s+(\w+)"),
    ],
    ".go": [
        re.compile(r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\("),
        re.compile(r"^func\s+(\w+)\s*\("),
    ],
    ".java": [
        re.compile(r"^\s*(?:public|private|protected)?\s*(?:static)?\s*(?:\w+)\s+(\w+)\s*\([^)]*\)\s*\{"),
    ],
    ".rb": [
        re.compile(r"^\s*def\s+(\w+)"),
        re.compile(r"^\s*class\s+(\w+)"),
    ],
    ".rs": [
        re.compile(r"^\s*(?:pub\s+)?fn\s+(\w+)\s*\("),
        re.compile(r"^\s*(?:pub\s+)?impl\s+(\w+)"),
    ],
    ".c": [
        re.compile(r"^\s*(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*\{"),
        re.compile(r"^\s*#define\s+(\w+)"),
    ],
    ".cpp": [
        re.compile(r"^\s*(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*\{"),
    ],
    ".h": [
        re.compile(r"^\s*(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*;"),
        re.compile(r"^\s*#define\s+(\w+)"),
    ],
}


def detect_functions(file_path: Path) -> list[dict]:
    """
    Return list of {name, line, indent} for each function/class defined in file.
    """
    suffix = file_path.suffix.lower()
    patterns = DEF_PATTERNS.get(suffix, [])
    if not patterns:
        return []

    try:
        lines = file_path.read_text(errors="ignore").splitlines()
    except Exception:
        return []

    functions = []
    for i, line in enumerate(lines, 1):
        for pat in patterns:
            m = pat.match(line)
            if m:
                groups = m.groups()
                # last group is always the name
                name = groups[-1].strip()
                indent = len(groups[0]) if groups[0] else 0
                functions.append({"name": name, "line": i, "indent": indent})
                break

    return functions


def anchor_from_file_line(
    file_path: Path,
    line_number: int | str,
    function_name: str | None = None,
) -> str:
    """
    Build an anchor string from a file:line or file:function context.
    """
    filename = str(file_path.resolve().relative_to(Path.cwd().resolve()))
    if function_name:
        return f"{filename}:{function_name}"
    return f"{filename}:{line_number}"


def parse_anchor(anchor: str) -> tuple[str, str | None, int | None]:
    """
    Parse an anchor into (filepath, function_name, line_number).
    Handles: src/a.py:42, src/a.py:func_name
    Returns (filepath, function_name or None, line_number or None)
    """
    if ":" not in anchor:
        return anchor, None, None

    path_part, anchor_part = anchor.rsplit(":", 1)

    # Try numeric line
    try:
        return path_part, None, int(anchor_part)
    except ValueError:
        return path_part, anchor_part, None


def resolve_anchor(anchor: str, repo_root: Optional[Path] = None) -> tuple[Path, str, int | None]:
    """
    Resolve an anchor string to a (file_path, function_name, line_number).
    """
    if repo_root is None:
        repo_root = Path.cwd()

    filepath, func_name, line_no = parse_anchor(anchor)
    full_path = (repo_root / filepath).resolve()
    return full_path, func_name, line_no