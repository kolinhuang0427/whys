"""
Whys CLI — Click-based command-line interface.
Usage: whys add <anchor> <reason>  |  whys explain <anchor>  |  whys list
"""

import os
import sys
import subprocess
from pathlib import Path

import click

from .parser import resolve_anchor, detect_functions, anchor_from_file_line
from .store import (
    save_annotation,
    get_annotation,
    list_annotations,
    search_annotations,
    load_annotations,
    _whys_dir,
)


def _git_user():
    try:
        name = subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
        email = subprocess.run(
            ["git", "config", "user.email"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
        return f"{name} <{email}>" if name else None
    except Exception:
        return None


def _repo_root():
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip() or None
        )
    except Exception:
        return None


@click.group()
def cli():
    """Whys — annotate code with reasons. Get 'why' when you need it."""
    pass


@cli.command("add")
@click.argument("anchor")
@click.argument("reason")
@click.option("--tag", "-t", multiple=True, help="Tags for this annotation")
def add(anchor, reason, tag):
    """
    Add a 'why' annotation to an anchor (file:line or file:function).

    Examples:
      whys add src/auth.py:42 "Handling JWT expiry edge case"
      whys add src/auth.py:validate_token "Legacy format — migrate after v2 launch"
    """
    try:
        root = Path(_repo_root() or Path.cwd())
        full_path, func_name, line_no = resolve_anchor(anchor, repo_root=root)

        # Detect function name if line number given
        display_anchor = anchor
        if line_no is not None and func_name is None:
            funcs = detect_functions(full_path)
            # find function at or before this line
            chosen = None
            for f in funcs:
                if f["line"] <= line_no:
                    chosen = f["name"]
                else:
                    break
            if chosen:
                func_name = chosen
                display_anchor = f"{anchor}:{func_name}"

        save_annotation(
            source_path=full_path,
            anchor=display_anchor,
            reason=reason,
            tags=list(tag) if tag else None,
            author=_git_user(),
            repo_root=root,
        )
        click.echo(f"✓ Annotation saved for {display_anchor}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("explain")
@click.argument("anchor")
def explain(anchor):
    """Show the reason behind a file:line or file:function anchor."""
    try:
        root = Path(_repo_root() or Path.cwd())
        full_path, func_name, line_no = resolve_anchor(anchor, repo_root=root)

        ann = get_annotation(full_path, anchor, repo_root=root)
        if ann:
            click.echo(f"📌 {anchor}")
            click.echo(f"   {ann['reason']}")
            if ann.get("author"):
                click.echo(f"   — {ann['author']} ({ann.get('created', 'unknown')})")
        else:
            click.echo(f"No annotation found for {anchor}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("list")
@click.argument("path", default=".", required=False)
@click.option("--tag", help="Filter by tag")
def list_cmd(path, tag):
    """
    List all annotations, optionally filtered by path prefix or tag.

    Examples:
      whys list
      whys list src/auth/
      whys list --tag security
    """
    try:
        root = Path(_repo_root() or Path.cwd())
        all_anns = list_annotations(repo_root=root)

        if path and path != ".":
            all_anns = [a for a in all_anns if path in a.get("_source", "")]

        if tag:
            all_anns = [a for a in all_anns if tag in a.get("tags", [])]

        if not all_anns:
            click.echo("No annotations found.")
            return

        for ann in all_anns:
            source = ann.get("_source", "?")
            anchor = ann.get("anchor", "?")
            reason = ann.get("reason", "")
            tags = ann.get("tags", [])
            created = ann.get("created", "")[:10]
            # anchor can be like "whys/cli.py:cli" or just "cli" - show full path
            if ":" not in anchor:
                display = f"{source}:{anchor}"
            else:
                display = anchor
            click.echo(display)
            click.echo(f"  └─ {reason}")
            if tags:
                click.echo(f"     tags: {', '.join(tags)}")
            click.echo(f"     {created}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("show")
@click.argument("file_path")
def show(file_path):
    """
    Show all annotations for a file, overlaid on function names.

    Example:
      whys show src/auth.py
    """
    try:
        root = Path(_repo_root() or Path.cwd())
        full_path = (root / file_path).resolve()
        if not full_path.exists():
            click.echo(f"File not found: {file_path}", err=True)
            sys.exit(1)

        functions = detect_functions(full_path)
        data = load_annotations(full_path, repo_root=root)

        ann_map = {}
        for ann in data.get("annotations", []):
            ann_map[ann.get("anchor", "")] = ann

        click.echo(f"\n{'# Whys':<20}  {'function':<30}  {'reason'}")
        click.echo("─" * 80)

        for func in functions:
            anchor = f"{file_path}:{func['name']}"
            ann = ann_map.get(anchor)
            prefix = "📌"
            reason = ann.get("reason", "") if ann else ""
            tags = ""
            if ann and ann.get("tags"):
                tags = f" [{', '.join(ann['tags'])}]"
            click.echo(f"{prefix:<20} {func['name']:<30} {reason}{tags}")

        uncovered = [
            ann for anchor, ann in ann_map.items()
            if file_path in anchor and
            not any(f"{file_path}:{f['name']}" == anchor for f in functions)
        ]
        if uncovered:
            click.echo(f"\n  Other annotations:")
            for ann in uncovered:
                click.echo(f"  └─ {ann.get('anchor')}: {ann.get('reason')}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("search")
@click.argument("query")
def search(query):
    """
    Search annotations by reason text.

    Example:
      whys search "migration"
    """
    try:
        root = Path(_repo_root() or Path.cwd())
        results = search_annotations(query, repo_root=root)
        if not results:
            click.echo(f"No annotations matching '{query}'")
            return
        for ann in results:
            source = ann.get("_source", "?")
            anchor = ann.get("anchor", "?")
            reason = ann.get("reason", "")
            click.echo(f"{source}:{anchor}")
            click.echo(f"  └─ {reason}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()