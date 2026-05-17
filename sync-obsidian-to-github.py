#!/usr/bin/env python3
"""Sync Obsidian 博客 → GitHub repo."""
import os
import shutil
import subprocess
import sys

VAULT_BLOG = os.path.expanduser("~/Documents/Obsidian Vault/博客")
SYNC_DIR = os.path.expanduser("~/Documents/blog-content-sync")


def main():
    if not os.path.isdir(VAULT_BLOG):
        print("[sync] Obsidian blog dir not found, skip.")
        sys.exit(0)

    # Pull latest from GitHub
    subprocess.run(["git", "-C", SYNC_DIR, "pull", "--rebase"], capture_output=True)

    # Copy blog content from Obsidian to sync dir
    changed = False
    for root, dirs, files in os.walk(VAULT_BLOG):
        rel = os.path.relpath(root, VAULT_BLOG)
        dest_dir = os.path.join(SYNC_DIR, rel) if rel != "." else SYNC_DIR
        os.makedirs(dest_dir, exist_ok=True)
        for fn in files:
            if not fn.endswith(".md"):
                continue
            src = os.path.join(root, fn)
            dst = os.path.join(dest_dir, fn)
            if _files_differ(src, dst):
                shutil.copy2(src, dst)
                print(f"  [COPY] {os.path.join(rel, fn)}")
                changed = True

    # Remove deleted files from sync dir
    obsidian_files = set()
    for root, dirs, files in os.walk(VAULT_BLOG):
        for fn in files:
            if fn.endswith(".md"):
                obsidian_files.add(os.path.relpath(os.path.join(root, fn), VAULT_BLOG))
    for root, dirs, files in os.walk(SYNC_DIR):
        for fn in files:
            if fn.endswith(".md") and fn != "README.md":
                rel = os.path.relpath(os.path.join(root, fn), SYNC_DIR)
                if rel not in obsidian_files and fn != "博客索引.md":
                    os.remove(os.path.join(root, fn))
                    print(f"  [DEL] {rel}")
                    changed = True

    if not changed:
        print("[sync] No changes.")
        return

    # Commit and push
    subprocess.run(["git", "-C", SYNC_DIR, "add", "-A"], capture_output=True)
    result = subprocess.run(
        ["git", "-C", SYNC_DIR, "commit", "-m", f"sync from Obsidian"],
        capture_output=True, text=True,
    )
    if "nothing to commit" not in result.stdout + result.stderr:
        push = subprocess.run(["git", "-C", SYNC_DIR, "push"], capture_output=True, text=True)
        if push.returncode == 0:
            print("[sync] Pushed to GitHub.")
        else:
            print(f"[sync] Push failed: {push.stderr}")
    else:
        print("[sync] Nothing to commit.")


def _files_differ(a, b):
    if not os.path.exists(b):
        return True
    try:
        with open(a, "r", encoding="utf-8") as fa, open(b, "r", encoding="utf-8") as fb:
            return fa.read() != fb.read()
    except Exception:
        return True


if __name__ == "__main__":
    main()
