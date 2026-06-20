#!/usr/bin/env python3
"""
博客双向同步脚本 — 适用于主电脑和其他电脑。
1. 从 GitHub pull 最新内容 → 写入 Obsidian
2. 检测 Obsidian 本地修改 → commit + push 到 GitHub
"""
import os
import shutil
import subprocess
import sys

VAULT_BLOG = os.path.expanduser("~/Documents/Obsidian Vault/博客")
SYNC_DIR = os.path.expanduser("~/Documents/blog-content-sync")
REPO_URL = "https://github.com/laoyutong/blog-content.git"

EXCLUDED_DIRS = {
    ".git",
    ".github",
    ".quartz-cache",
    "node_modules",
    "public",
    "quartz",
    "site",
}
PROTECTED_REPO_FILES = {"README.md"}


def setup():
    if os.path.isdir(SYNC_DIR):
        print("[setup] Already exists.")
        return
    print(f"[setup] Cloning {REPO_URL} ...")
    subprocess.run(["git", "clone", REPO_URL, SYNC_DIR], check=True)
    print("[setup] Done.")


def sync():
    if not os.path.isdir(SYNC_DIR):
        print("[sync] Run setup first.")
        sys.exit(1)

    # ── Step 1: Pull from GitHub, write to Obsidian ──
    os.makedirs(VAULT_BLOG, exist_ok=True)
    result = subprocess.run(
        ["git", "-C", SYNC_DIR, "pull", "--rebase"],
        capture_output=True, text=True,
    )
    pulled = "Already up to date" not in result.stdout

    if pulled:
        changed = 0
        for root, dirs, files in os.walk(SYNC_DIR):
            _prune_dirs(dirs)
            rel = os.path.relpath(root, SYNC_DIR)
            dest_dir = VAULT_BLOG if rel == "." else os.path.join(VAULT_BLOG, rel)
            os.makedirs(dest_dir, exist_ok=True)
            for fn in files:
                src = os.path.join(root, fn)
                rel_file = os.path.relpath(src, SYNC_DIR)
                if not _is_note_path(rel_file):
                    continue
                dst = os.path.join(dest_dir, fn)
                with open(src, encoding="utf-8") as f:
                    content = f.read()
                if not os.path.exists(dst) or open(dst, encoding="utf-8").read() != content:
                    with open(dst, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"  [↓] {os.path.join(rel, fn)}")
                    changed += 1
        print(f"[↓] Pulled {changed} updated files from GitHub → Obsidian")

    # ── Step 2: Detect Obsidian changes, push to GitHub ──
    push_changed = False
    for root, dirs, files in os.walk(VAULT_BLOG):
        _prune_dirs(dirs)
        rel = os.path.relpath(root, VAULT_BLOG)
        dest_dir = os.path.join(SYNC_DIR, rel) if rel != "." else SYNC_DIR
        os.makedirs(dest_dir, exist_ok=True)
        for fn in files:
            src = os.path.join(root, fn)
            rel_file = os.path.relpath(src, VAULT_BLOG)
            if not _is_note_path(rel_file):
                continue
            dst = os.path.join(dest_dir, fn)
            if _differ(src, dst):
                shutil.copy2(src, dst)
                print(f"  [↑] {os.path.join(rel, fn)}")
                push_changed = True

    # Remove deleted notes from sync dir
    obsidian_files = set()
    for root, dirs, files in os.walk(VAULT_BLOG):
        _prune_dirs(dirs)
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), VAULT_BLOG)
            if _is_note_path(rel):
                obsidian_files.add(rel)
    for root, dirs, files in os.walk(SYNC_DIR):
        _prune_dirs(dirs)
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), SYNC_DIR)
            if _is_note_path(rel) and rel not in obsidian_files:
                os.remove(os.path.join(root, fn))
                print(f"  [↑ DEL] {rel}")
                push_changed = True

    if push_changed:
        subprocess.run(["git", "-C", SYNC_DIR, "add", "-A"], capture_output=True)
        result = subprocess.run(
            ["git", "-C", SYNC_DIR, "commit", "-m", "sync from Obsidian"],
            capture_output=True, text=True,
        )
        if "nothing to commit" not in result.stdout + result.stderr:
            push = subprocess.run(["git", "-C", SYNC_DIR, "push"], capture_output=True, text=True)
            if push.returncode == 0:
                print("[↑] Pushed to GitHub.")
            else:
                print(f"[↑] Push failed: {push.stderr}")

    if not pulled and not push_changed:
        print("[sync] Already up to date.")


def _prune_dirs(dirs):
    dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]


def _is_note_path(rel_path):
    parts = rel_path.split(os.sep)
    if not rel_path.endswith(".md"):
        return False
    if parts[0] in EXCLUDED_DIRS or parts[0].startswith("."):
        return False
    if len(parts) == 1 and parts[0] in PROTECTED_REPO_FILES:
        return False
    return True


def _differ(a, b):
    if not os.path.exists(b):
        return True
    try:
        with open(a, encoding="utf-8") as fa, open(b, encoding="utf-8") as fb:
            return fa.read() != fb.read()
    except Exception:
        return True


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sync"
    if cmd == "setup":
        setup()
    else:
        sync()
