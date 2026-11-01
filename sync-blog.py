#!/usr/bin/env python3
"""Sync Markdown notes using a last-successful-sync baseline."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

VAULT_BLOG = Path(os.environ.get("BLOG_VAULT", "~/Documents/Obsidian Vault/博客")).expanduser()
SYNC_DIR = Path(os.environ.get("BLOG_SYNC_DIR", Path(__file__).resolve().parent)).expanduser()
REPO_URL = "https://github.com/laoyutong/blog-content.git"
EXCLUDED_DIRS = {"node_modules", "public", "quartz", "site", "content", "docs", "tests"}
PROTECTED_REPO_FILES = {"README.md", "AGENTS.md"}


def git(*args):
    return subprocess.run(
        ["git", "--literal-pathspecs", "-C", str(SYNC_DIR), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def notes(directory):
    result = {}
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
        for name in dirs:
            if (Path(root) / name).is_symlink():
                raise RuntimeError(f"Refusing symlink directory: {Path(root) / name}")
        for name in files:
            path = Path(root) / name
            rel = path.relative_to(directory).as_posix()
            if name.endswith(".md") and rel not in PROTECTED_REPO_FILES:
                if path.is_symlink():
                    raise RuntimeError(f"Refusing symlink note: {path}")
                result[rel] = path.read_bytes().decode("utf-8")
    return result


def merge(base, local, remote):
    """Resolve independent edits; refuse edit/edit and edit/delete conflicts."""
    merged, conflicts = {}, []
    for name in sorted(base.keys() | local.keys() | remote.keys()):
        before, ours, theirs = base.get(name), local.get(name), remote.get(name)
        if ours == theirs:
            value = ours
        elif ours == before:
            value = theirs
        elif theirs == before:
            value = ours
        else:
            conflicts.append(name)
            continue
        if value is not None:
            merged[name] = value
    if conflicts:
        raise RuntimeError("Conflicting notes; reconcile both copies and retry:\n  " + "\n  ".join(conflicts))
    return merged


def apply(directory, current, desired):
    for name in sorted(current.keys() | desired.keys()):
        if current.get(name) == desired.get(name):
            continue
        path = directory / name
        if name not in desired:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(desired[name].encode("utf-8"))


def setup():
    if SYNC_DIR.exists():
        print("[setup] Directory already exists.")
        return
    subprocess.run(["git", "clone", REPO_URL, str(SYNC_DIR)], check=True)


def sync():
    if not VAULT_BLOG.is_dir():
        raise RuntimeError(f"Obsidian directory is missing: {VAULT_BLOG}")
    if git("status", "--porcelain"):
        raise RuntimeError("Repository has uncommitted changes. Commit or stash them before syncing.")
    state_path = Path(git("rev-parse", "--absolute-git-dir")) / "blog-sync-state.json"
    base = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    local = notes(VAULT_BLOG)
    # Fetch/pull errors stop the operation before any Obsidian files are changed.
    git("pull", "--ff-only")
    remote = notes(SYNC_DIR)
    desired = merge(base, local, remote)
    # Obsidian may have changed while the network request was running.
    if notes(VAULT_BLOG) != local:
        raise RuntimeError("Obsidian changed during sync. Please retry.")
    changed = sorted(name for name in remote.keys() | desired.keys()
                     if remote.get(name) != desired.get(name))
    apply(SYNC_DIR, remote, desired)
    if changed:
        git("add", "--", *changed)
        git("commit", "-m", "sync from Obsidian", "--", *changed)
    # Always retry a previously failed push, even when there are no new edits.
    git("push")
    if notes(VAULT_BLOG) != local:
        raise RuntimeError("Obsidian changed during push. Repository is synced; retry to reconcile notes.")
    apply(VAULT_BLOG, local, desired)
    state_path.with_suffix(".tmp").write_text(json.dumps(desired, ensure_ascii=False), encoding="utf-8")
    state_path.with_suffix(".tmp").replace(state_path)
    print(f"[sync] Synced {len(desired)} notes ({len(changed)} repository changes).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="sync", choices=["setup", "sync"])
    args = parser.parse_args()
    try:
        setup() if args.command == "setup" else sync()
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"[sync] {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr or "", file=sys.stderr)
        sys.exit(1)
