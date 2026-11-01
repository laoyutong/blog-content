import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("blog_sync", Path(__file__).resolve().parents[1] / "sync-blog.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class MergeTests(unittest.TestCase):
    def test_first_sync_preserves_both_sides(self):
        self.assertEqual(sync.merge({}, {"a.md": "a"}, {"b.md": "b"}), {"a.md": "a", "b.md": "b"})

    def test_conflicts(self):
        for local in ({"a.md": "local"}, {}):
            with self.assertRaises(RuntimeError):
                sync.merge({"a.md": "base"}, local, {"a.md": "remote"})

    def test_deletions_in_both_directions(self):
        self.assertEqual(sync.merge({"a.md": "a", "b.md": "b"}, {"a.md": "a"}, {"b.md": "b"}), {})


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.repo = self.root / "repo"
        self.vault = self.root / "vault"
        self.vault.mkdir()
        self.run_git(self.root, "init", "--bare", str(self.remote))
        self.run_git(self.root, "clone", str(self.remote), str(self.repo))
        self.run_git(self.repo, "config", "user.name", "Test")
        self.run_git(self.repo, "config", "user.email", "test@example.com")
        self.run_git(self.repo, "config", "commit.gpgsign", "false")
        (self.repo / "a.md").write_text("base")
        self.run_git(self.repo, "add", ".")
        self.run_git(self.repo, "commit", "-m", "initial")
        self.run_git(self.repo, "push", "-u", "origin", "HEAD")
        self.old_paths = sync.SYNC_DIR, sync.VAULT_BLOG
        sync.SYNC_DIR, sync.VAULT_BLOG = self.repo, self.vault
        self.addCleanup(self.restore)

    def restore(self):
        sync.SYNC_DIR, sync.VAULT_BLOG = self.old_paths

    def run_git(self, cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)

    def test_roundtrip_and_remote_deletion(self):
        sync.sync()
        self.assertEqual((self.vault / "a.md").read_text(), "base")
        (self.vault / "a.md").write_text("local")
        sync.sync()
        self.assertEqual((self.repo / "a.md").read_text(), "local")
        self.run_git(self.repo, "rm", "a.md")
        self.run_git(self.repo, "commit", "-m", "delete")
        sync.sync()
        self.assertFalse((self.vault / "a.md").exists())

    def test_local_deletion(self):
        sync.sync()
        (self.vault / "a.md").unlink()
        sync.sync()
        self.assertFalse((self.repo / "a.md").exists())

    def test_dirty_repo_stops_without_touching_vault(self):
        (self.repo / "unrelated.txt").write_text("keep")
        self.run_git(self.repo, "add", "unrelated.txt")
        with self.assertRaises(RuntimeError):
            sync.sync()
        self.assertEqual(list(self.vault.iterdir()), [])

    def test_failed_push_can_retry(self):
        sync.sync()
        (self.vault / "a.md").write_text("edited")
        hook = self.remote / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        with self.assertRaises(subprocess.CalledProcessError):
            sync.sync()
        hook.unlink()
        sync.sync()
        self.assertEqual((self.repo / "a.md").read_text(), "edited")
        self.assertEqual(sync.git("rev-parse", "HEAD"), sync.git("rev-parse", "@{u}"))

    def test_pull_failure_preserves_vault(self):
        (self.vault / "a.md").write_text("local")
        self.run_git(self.repo, "remote", "set-url", "origin", str(self.root / "missing"))
        with self.assertRaises(subprocess.CalledProcessError):
            sync.sync()
        self.assertEqual((self.vault / "a.md").read_text(), "local")
        self.assertEqual((self.repo / "a.md").read_text(), "base")

    def test_conflict_preserves_both_copies(self):
        sync.sync()
        (self.vault / "a.md").write_text("local")
        (self.repo / "a.md").write_text("remote")
        self.run_git(self.repo, "commit", "-am", "remote change")
        with self.assertRaises(RuntimeError):
            sync.sync()
        self.assertEqual((self.vault / "a.md").read_text(), "local")
        self.assertEqual((self.repo / "a.md").read_text(), "remote")
