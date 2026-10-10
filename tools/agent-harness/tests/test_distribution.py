"""Portable installer ownership and path-safety contracts."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[3]
MANIFEST = ".agent-harness-install.json"
sys.path.insert(0, str(REPO / "tools/agent-harness"))

from agent_harness import distribution  # noqa: E402


class DistributionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def git(self, repo, *args, check=True):
        return subprocess.run(["git", *args], cwd=repo, text=True,
                              capture_output=True, check=check)

    def repository(self, name="host", *, commit=True):
        repo = self.root / name
        repo.mkdir()
        self.git(repo, "init", "-b", "main")
        self.git(repo, "config", "user.email", "harness@example.invalid")
        self.git(repo, "config", "user.name", "Harness Test")
        if commit:
            (repo / "host.txt").write_text("host\n", encoding="utf-8")
            self.git(repo, "add", "host.txt")
            self.git(repo, "commit", "-m", "host fixture")
        return repo

    def run_script(self, name, target):
        return subprocess.run([str(REPO / name), str(target)], cwd=REPO,
                              text=True, capture_output=True, check=False,
                              env={**os.environ, "TZ": "UTC"})

    def test_install_accepts_linked_worktree_and_seeds_complete_host_contract(self):
        primary = self.repository("primary")
        linked = self.root / "linked"
        self.git(primary, "worktree", "add", "-b", "feat/adopt", str(linked))

        result = self.run_script("install.sh", linked)

        self.assertEqual(result.returncode, 0, result.stderr)
        host = json.loads((linked / "docs/agent/HARNESS_HOST.json").read_text())
        referenced = (
            host["activePlan"], host["deliveryManifest"], host["ledger"],
            host["fixture"]["path"], host["fixture"]["planPath"],
        )
        for relative in referenced:
            self.assertTrue((linked / relative).is_file(), relative)
        manifest = json.loads((linked / MANIFEST).read_text())
        self.assertEqual(manifest["formatVersion"], 1)
        self.assertTrue(manifest["ownedFiles"])
        for entry in manifest["ownedFiles"]:
            path = linked / entry["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["sha256"])

    def test_install_rejects_unborn_repository_without_writing(self):
        repo = self.repository(commit=False)

        result = self.run_script("install.sh", repo)

        self.assertEqual(result.returncode, 2)
        self.assertFalse((repo / MANIFEST).exists())
        self.assertFalse((repo / "scripts").exists())
        self.assertFalse((repo / "tools").exists())

    def test_install_never_overwrites_host_files(self):
        repo = self.repository()
        wrapper = repo / "scripts/agent-harness"
        wrapper.parent.mkdir()
        wrapper.write_text("host-owned\n", encoding="utf-8")

        result = self.run_script("install.sh", repo)

        self.assertEqual(result.returncode, 3)
        self.assertEqual(wrapper.read_text(), "host-owned\n")
        self.assertFalse((repo / MANIFEST).exists())

    def test_install_rejects_symlinked_runtime_ancestors_without_outside_write(self):
        for relative in ("scripts", "tools", "tools/agent-harness", "docs", "tests"):
            with self.subTest(relative=relative):
                repo = self.repository("host-" + relative.replace("/", "-"))
                outside = self.root / ("outside-" + relative.replace("/", "-"))
                outside.mkdir()
                link = repo / relative
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(outside, target_is_directory=True)

                result = self.run_script("install.sh", repo)

                self.assertEqual(result.returncode, 3)
                self.assertEqual(list(outside.iterdir()), [])
                self.assertFalse((repo / MANIFEST).exists())

    def test_upgrade_refuses_modified_owned_file_and_symlinked_parent(self):
        repo = self.repository()
        self.assertEqual(self.run_script("install.sh", repo).returncode, 0)
        wrapper = repo / "scripts/agent-harness"
        wrapper.write_text("host replacement\n", encoding="utf-8")
        modified = self.run_script("upgrade.sh", repo)
        self.assertEqual(modified.returncode, 3)
        self.assertEqual(wrapper.read_text(), "host replacement\n")

        wrapper.unlink()
        outside = self.root / "outside-upgrade"
        outside.mkdir()
        (repo / "scripts").rmdir()
        (repo / "scripts").symlink_to(outside, target_is_directory=True)
        linked = self.run_script("upgrade.sh", repo)
        self.assertEqual(linked.returncode, 3)
        self.assertEqual(list(outside.iterdir()), [])

    def test_uninstall_only_deletes_hash_matching_owned_files(self):
        repo = self.repository()
        self.assertEqual(self.run_script("install.sh", repo).returncode, 0)
        host_policy = repo / "docs/agent/PROJECT_MEMORY.md"
        host_policy.parent.mkdir(parents=True, exist_ok=True)
        host_policy.write_text("custom host policy\n", encoding="utf-8")
        extra = repo / "tools/agent-harness/host-owned.txt"
        extra.write_text("keep\n", encoding="utf-8")
        wrapper = repo / "scripts/agent-harness"
        wrapper.write_text("changed\n", encoding="utf-8")

        refused = self.run_script("uninstall.sh", repo)

        self.assertEqual(refused.returncode, 3)
        self.assertTrue((repo / MANIFEST).is_file())
        self.assertEqual(wrapper.read_text(), "changed\n")
        self.assertEqual(extra.read_text(), "keep\n")
        self.assertEqual(host_policy.read_text(), "custom host policy\n")

    def test_uninstall_rejects_symlinked_owned_parent_without_outside_delete(self):
        repo = self.repository()
        self.assertEqual(self.run_script("install.sh", repo).returncode, 0)
        outside = self.root / "outside-uninstall"
        outside.mkdir()
        sentinel = outside / "agent-harness"
        sentinel.write_text("outside\n", encoding="utf-8")
        wrapper = repo / "scripts/agent-harness"
        wrapper.unlink()
        (repo / "scripts").rmdir()
        (repo / "scripts").symlink_to(outside, target_is_directory=True)

        result = self.run_script("uninstall.sh", repo)

        self.assertEqual(result.returncode, 3)
        self.assertEqual(sentinel.read_text(), "outside\n")
        self.assertTrue((repo / MANIFEST).is_file())

    def test_uninstall_rejects_manifest_path_injection_before_deleting_anything(self):
        repo = self.repository()
        self.assertEqual(self.run_script("install.sh", repo).returncode, 0)
        manifest_path = repo / MANIFEST
        manifest = json.loads(manifest_path.read_text())
        manifest["ownedFiles"][0]["path"] = "../host.txt"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = self.run_script("uninstall.sh", repo)

        self.assertEqual(result.returncode, 3)
        self.assertEqual((repo / "host.txt").read_text(), "host\n")
        self.assertTrue((repo / "scripts/agent-harness").is_file())

    def test_uninstall_rejects_manifest_claim_on_allowed_but_unowned_path(self):
        repo = self.repository()
        self.assertEqual(self.run_script("install.sh", repo).returncode, 0)
        host_file = repo / "tools/agent-harness/agent_harness/host_owned.py"
        host_file.write_text("host owned\n", encoding="utf-8")
        manifest_path = repo / MANIFEST
        manifest = json.loads(manifest_path.read_text())
        manifest["ownedFiles"].append({
            "path": "tools/agent-harness/agent_harness/host_owned.py",
            "sha256": hashlib.sha256(host_file.read_bytes()).hexdigest(),
            "mode": "0644",
        })
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = self.run_script("uninstall.sh", repo)

        self.assertEqual(result.returncode, 3)
        self.assertEqual(host_file.read_text(), "host owned\n")
        self.assertTrue((repo / "scripts/agent-harness").is_file())

    def test_write_rejects_ancestor_swapped_to_symlink_after_path_check(self):
        repo = self.repository()
        parent = repo / "tools/agent-harness/agent_harness"
        parent.mkdir(parents=True)
        outside = self.root / "outside-race"
        (outside / "agent-harness/agent_harness").mkdir(parents=True)
        real_open = os.open
        swapped = False

        def swap_before_parent_open(path, *args, **kwargs):
            nonlocal swapped
            opens_checked_parent = Path(path) == parent and kwargs.get("dir_fd") is None
            opens_checked_ancestor = path == "tools" and kwargs.get("dir_fd") is not None
            if not swapped and (opens_checked_parent or opens_checked_ancestor):
                parent.rmdir()
                (repo / "tools/agent-harness").rmdir()
                (repo / "tools").rmdir()
                (repo / "tools").symlink_to(outside, target_is_directory=True)
                swapped = True
            return real_open(path, *args, **kwargs)

        with mock.patch.object(distribution.os, "open", side_effect=swap_before_parent_open):
            with self.assertRaises(distribution.DistributionError):
                distribution._write_new(
                    repo, "tools/agent-harness/agent_harness/new.py", b"owned\n", 0o644,
                )

        self.assertTrue(swapped)
        self.assertFalse((outside / "agent-harness/agent_harness/new.py").exists())

    def test_prune_cannot_remove_outside_directory_after_ancestor_swap(self):
        repo = self.repository()
        local = repo / "tools/agent-harness"
        local.mkdir(parents=True)
        outside = self.root / "outside-prune"
        (outside / "agent-harness").mkdir(parents=True)
        real_rmdir = os.rmdir
        swapped = False

        def swap_before_rmdir(path, *args, **kwargs):
            nonlocal swapped
            old_style = Path(path) == local and kwargs.get("dir_fd") is None
            anchored_style = path == "agent-harness" and kwargs.get("dir_fd") is not None
            if not swapped and (old_style or anchored_style):
                real_rmdir(local)
                real_rmdir(repo / "tools")
                (repo / "tools").symlink_to(outside, target_is_directory=True)
                swapped = True
            return real_rmdir(path, *args, **kwargs)

        with mock.patch.object(distribution.os, "rmdir", side_effect=swap_before_rmdir):
            distribution._prune(repo, ["tools/agent-harness/owned.py"])

        self.assertTrue(swapped)
        self.assertTrue((outside / "agent-harness").is_dir())


if __name__ == "__main__":
    unittest.main()
