#!/usr/bin/env python3
"""从 GitHub 拉取博客内容到 Obsidian（在其他电脑上使用）"""
import os
import shutil
import subprocess
import sys

VAULT_BLOG = os.path.expanduser("~/Documents/Obsidian Vault/博客")
SYNC_DIR = os.path.expanduser("~/Documents/blog-content-sync")
REPO_URL = "https://github.com/laoyutong/blog-content.git"


def setup():
    """首次运行：clone 仓库"""
    if os.path.isdir(SYNC_DIR):
        print("[setup] Sync dir already exists.")
        return
    print(f"[setup] Cloning {REPO_URL} ...")
    subprocess.run(["git", "clone", REPO_URL, SYNC_DIR], check=True)


def pull():
    """从 GitHub 拉取，写入 Obsidian"""
    if not os.path.isdir(SYNC_DIR):
        print("[pull] Run setup first.")
        sys.exit(1)

    # Pull latest
    result = subprocess.run(
        ["git", "-C", SYNC_DIR, "pull", "--rebase"],
        capture_output=True, text=True,
    )
    if "Already up to date" in result.stdout:
        print("[pull] Already up to date.")
        return

    # Copy files to Obsidian vault
    os.makedirs(VAULT_BLOG, exist_ok=True)
    changed = 0
    for root, dirs, files in os.walk(SYNC_DIR):
        # Skip .git
        if ".git" in root:
            continue
        rel = os.path.relpath(root, SYNC_DIR)
        if rel == ".":
            continue
        dest_dir = os.path.join(VAULT_BLOG, rel)
        os.makedirs(dest_dir, exist_ok=True)
        for fn in files:
            if not fn.endswith(".md"):
                continue
            src = os.path.join(root, fn)
            dst = os.path.join(dest_dir, fn)
            with open(src, encoding="utf-8") as f:
                content = f.read()
            if not os.path.exists(dst) or open(dst, encoding="utf-8").read() != content:
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  [OK] {os.path.join(rel, fn)}")
                changed += 1

    print(f"[pull] Updated {changed} files.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup()
    else:
        pull()
