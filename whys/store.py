"""
Annotation store backed by YAML files.
One .yaml file per source file, stored in .whys/ at repo root.
"""

import datetime
from pathlib import Path
from typing import Optional
import yaml


def _whys_dir(repo_root: Optional[Path] = None) -> Path:
    if repo_root is None:
        repo_root = Path.cwd()
    return repo_root / ".whys"


def _yaml_path(source_path: Path, repo_root: Optional[Path] = None) -> Path:
    """Return the .whys YAML path for a given source file."""
    if repo_root is None:
        repo_root = Path.cwd()
    try:
        rel = source_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        rel = source_path.resolve().relative_to(Path.cwd().resolve())
    whys_dir = _whys_dir(repo_root)
    yaml_name = str(rel).replace("/", "__").replace("\\", "__") + ".yaml"
    return whys_dir / yaml_name


def _source_from_yaml_filename(yaml_path: Path) -> str:
    """Reconstruct source file path from .whys/xxxx.yaml filename."""
    return yaml_path.stem.replace("__", "/")


def load_annotations(source_path: Path, repo_root: Optional[Path] = None) -> dict:
    """Load all annotations for a source file."""
    path = _yaml_path(source_path, repo_root)
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
            return data if data else {}
    except Exception:
        return {}


def save_annotation(
    source_path: Path,
    anchor: str,
    reason: str,
    tags: list[str] | None = None,
    author: str | None = None,
    repo_root: Optional[Path] = None,
) -> None:
    """Save a new annotation for a function or line range."""
    path = _yaml_path(source_path, repo_root)
    data = load_annotations(source_path, repo_root)

    annotations = data.get("annotations", [])
    for ann in annotations:
        if ann.get("anchor") == anchor:
            ann["reason"] = reason
            ann["tags"] = tags or ann.get("tags", [])
            ann["updated"] = datetime.datetime.now().isoformat()
            if author:
                ann["author"] = author
            break
    else:
        annotations.append({
            "anchor": anchor,
            "reason": reason,
            "author": author,
            "created": datetime.datetime.now().isoformat(),
            "tags": tags or [],
        })

    data["annotations"] = annotations
    whys_dir = _whys_dir(repo_root or source_path.parent)
    whys_dir.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def get_annotation(source_path: Path, anchor: str, repo_root: Optional[Path] = None) -> dict | None:
    """Get annotation for a specific anchor."""
    data = load_annotations(source_path, repo_root)
    for ann in data.get("annotations", []):
        if ann.get("anchor") == anchor:
            return ann
    return None


def list_annotations(repo_root: Optional[Path] = None) -> list[dict]:
    """List all annotations across the repo."""
    whys_dir = _whys_dir(repo_root)
    if not whys_dir.exists():
        return []
    all_annotations = []
    for yaml_file in whys_dir.glob("*.yaml"):
        try:
            with open(yaml_file, "r") as f:
                data = yaml.safe_load(f) or {}
                for ann in data.get("annotations", []):
                    rel = _source_from_yaml_filename(yaml_file)
                    ann["_source"] = rel
                    all_annotations.append(ann)
        except Exception:
            continue
    return all_annotations


def search_annotations(query: str, repo_root: Optional[Path] = None) -> list[dict]:
    """Search annotations whose reason contains the query string."""
    q = query.lower()
    return [
        ann for ann in list_annotations(repo_root)
        if q in ann.get("reason", "").lower() or q in ann.get("anchor", "").lower()
    ]