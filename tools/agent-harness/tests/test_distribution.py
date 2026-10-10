"""Portable installer ownership and path-safety contracts."""

import hashlib
import json
import os
from pathlib import Path
import re
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

    def installed_suite(self, repo):
        manifest_path = repo / MANIFEST
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = {
            entry["path"]: (repo / entry["path"]).read_bytes()
            for entry in manifest["ownedFiles"]
        }
        return manifest_path.read_bytes(), files

    def add_baseline_checkout(self):
        checkout = self.root / "baseline-4727ca9"
        self.git(REPO, "worktree", "add", "--detach", str(checkout), "4727ca9")
        self.addCleanup(lambda: self.git(REPO, "worktree", "remove", "--force", str(checkout),
                                         check=False))
        return checkout

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
        self.assertEqual(manifest["formatVersion"], distribution.FORMAT_VERSION)
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

    def test_upgrade_migrates_real_4727ca9_install_to_json_manifest(self):
        baseline = self.add_baseline_checkout()
        repo = self.repository()

        installed = subprocess.run([str(baseline / "install.sh"), str(repo)], cwd=baseline,
                                   text=True, capture_output=True, check=False)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        self.assertTrue((repo / ".agent-harness-install").is_file())

        upgraded = self.run_script("upgrade.sh", repo)

        self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
        self.assertFalse((repo / ".agent-harness-install").exists())
        manifest = json.loads((repo / MANIFEST).read_text(encoding="utf-8"))
        self.assertEqual(manifest["formatVersion"], distribution.FORMAT_VERSION)
        self.assertEqual({entry["path"] for entry in manifest["ownedFiles"]},
                         set(distribution.RUNTIME_FILES))

    def test_upgrade_rejects_regular_file_swap_after_verification_for_replace_and_unlink(self):
        for operation in ("replace", "unlink"):
            with self.subTest(operation=operation):
                repo = self.repository("host-race-" + operation)
                self.assertEqual(self.run_script("install.sh", repo).returncode, 0)
                manifest = json.loads((repo / MANIFEST).read_text(encoding="utf-8"))
                target_relative = ("tools/agent-harness/agent_harness/cli.py" if operation == "replace"
                                   else "tools/agent-harness/agent_harness/doctor.py")
                target = repo / target_relative
                real_verify = distribution._verify_owned
                swapped = False
                verify_calls = 0

                def verify_then_swap(root, entries):
                    nonlocal swapped, verify_calls
                    identities = real_verify(root, entries)
                    verify_calls += 1
                    if not swapped and verify_calls == 2:
                        replacement = target.with_name(target.name + ".replacement")
                        replacement.write_text("host replacement\n", encoding="utf-8")
                        replacement.chmod(target.stat().st_mode & 0o777)
                        os.replace(replacement, target)
                        swapped = True
                    return identities

                inventory = distribution._source_inventory(REPO)
                if operation == "unlink":
                    inventory = [(entry, content) for entry, content in inventory
                                 if entry["path"] != target_relative]
                with mock.patch.object(distribution, "_verify_owned", side_effect=verify_then_swap), \
                        mock.patch.object(distribution, "_source_inventory", return_value=inventory):
                    with self.assertRaises(distribution.DistributionError):
                        distribution.upgrade(REPO, repo)

                self.assertTrue(swapped)
                self.assertEqual(target.read_text(encoding="utf-8"), "host replacement\n")
                self.assertTrue((repo / MANIFEST).is_file())

    def test_manifest_schema_allows_new_version_to_add_and_remove_owned_files(self):
        repo = self.repository()
        self.assertEqual(self.run_script("install.sh", repo).returncode, 0)
        old_manifest = json.loads((repo / MANIFEST).read_text(encoding="utf-8"))
        old_paths = {entry["path"] for entry in old_manifest["ownedFiles"]}
        removed = "tools/agent-harness/agent_harness/doctor.py"
        added = "tools/agent-harness/agent_harness/new_runtime.py"
        inventory = [item for item in distribution._source_inventory(REPO)
                     if item[0]["path"] != removed]
        added_content = b"VALUE = 'new runtime'\n"
        inventory.append((distribution._entry(added, added_content, 0o644), added_content))
        new_paths = old_paths - {removed} | {added}

        old_format = old_manifest["formatVersion"]
        new_format = old_format + 1
        schema_state = {
            "FORMAT_VERSION": new_format,
            "MANIFEST_FILE_SETS": {
                old_format: frozenset(old_paths), new_format: frozenset(new_paths),
            },
        }
        with mock.patch.dict(distribution.__dict__, schema_state), \
                mock.patch.object(distribution, "_source_inventory", return_value=inventory):
            try:
                distribution.upgrade(REPO, repo)
                loaded = distribution._load_manifest(repo)
            except distribution.DistributionError as error:
                self.fail(f"versioned ownership schema rejected a legal inventory change: {error}")

        self.assertEqual(loaded[0]["formatVersion"], new_format)
        self.assertEqual({entry["path"] for entry in loaded[0]["ownedFiles"]}, new_paths)
        self.assertFalse((repo / removed).exists())
        self.assertEqual((repo / added).read_bytes(), added_content)

    def test_upgrade_rejects_original_target_root_or_ancestor_symlink(self):
        for kind in ("root", "ancestor"):
            with self.subTest(kind=kind):
                parent = self.root / ("real-parent-" + kind)
                parent.mkdir()
                repo = parent / "host"
                repo.mkdir()
                self.git(repo, "init", "-b", "main")
                self.git(repo, "config", "user.email", "harness@example.invalid")
                self.git(repo, "config", "user.name", "Harness Test")
                (repo / "host.txt").write_text("host\n", encoding="utf-8")
                self.git(repo, "add", "host.txt")
                self.git(repo, "commit", "-m", "host fixture")
                self.assertEqual(self.run_script("install.sh", repo).returncode, 0)
                if kind == "root":
                    target = self.root / "host-link"
                    target.symlink_to(repo, target_is_directory=True)
                else:
                    alias = self.root / "parent-link"
                    alias.symlink_to(parent, target_is_directory=True)
                    target = alias / "host"

                result = self.run_script("upgrade.sh", target)

                self.assertEqual(result.returncode, 2, result.stderr or result.stdout)

    def test_upgrade_rolls_back_complete_suite_after_runtime_or_manifest_replace_failure(self):
        for failed_path in ("tools/agent-harness/agent_harness/cli.py", MANIFEST):
            with self.subTest(failed_path=failed_path):
                repo = self.repository("host-" + failed_path.replace("/", "-"))
                self.assertEqual(self.run_script("install.sh", repo).returncode, 0)
                old_manifest, old_files = self.installed_suite(repo)
                real_replace = distribution._replace
                injected = False

                def fail_once(root, relative, content, mode, **kwargs):
                    nonlocal injected
                    if relative == failed_path and not injected:
                        injected = True
                        raise distribution.DistributionError("injected replace failure")
                    return real_replace(root, relative, content, mode, **kwargs)

                with mock.patch.object(distribution, "_replace", side_effect=fail_once):
                    with self.assertRaises(distribution.DistributionError) as raised:
                        distribution.upgrade(REPO, repo)

                self.assertTrue(injected)
                self.assertIn("恢复结果：成功", str(raised.exception))
                self.assertRegex(str(raised.exception),
                                 r"备份位置：\.agent-harness-backups/[0-9TZ-]+")
                self.assertNotIn(str(repo), str(raised.exception))
                restored_manifest, restored_files = self.installed_suite(repo)
                self.assertEqual(restored_manifest, old_manifest)
                self.assertEqual(restored_files, old_files)

                distribution.upgrade(REPO, repo)
                retried_manifest, retried_files = self.installed_suite(repo)
                self.assertEqual(retried_manifest, old_manifest)
                self.assertEqual(retried_files, old_files)

    def test_upgrade_reports_failed_rollback_and_keeps_verified_backup(self):
        repo = self.repository()
        self.assertEqual(self.run_script("install.sh", repo).returncode, 0)
        real_replace = distribution._replace
        calls = 0

        def fail_upgrade_and_restore(root, relative, content, mode, **kwargs):
            nonlocal calls
            calls += 1
            if calls in (2, 3):
                raise distribution.DistributionError("injected transaction failure")
            return real_replace(root, relative, content, mode, **kwargs)

        with mock.patch.object(distribution, "_replace", side_effect=fail_upgrade_and_restore):
            with self.assertRaises(distribution.DistributionError) as raised:
                distribution.upgrade(REPO, repo)

        message = str(raised.exception)
        self.assertIn("恢复结果：失败", message)
        match = re.search(r"备份位置：(\.agent-harness-backups/[^；]+)", message)
        self.assertIsNotNone(match)
        backup = repo / match.group(1)
        backup_manifest = json.loads((backup / MANIFEST).read_text(encoding="utf-8"))
        for entry in backup_manifest["ownedFiles"]:
            content = (backup / entry["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), entry["sha256"])

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

    def test_write_new_removes_unpublished_file_when_write_fails(self):
        repo = self.repository()
        relative = "tools/agent-harness/agent_harness/new.py"
        with mock.patch.object(distribution.os, "fsync",
                               side_effect=OSError("injected publication failure")):
            with self.assertRaises(distribution.DistributionError):
                distribution._write_new(repo, relative, b"owned\n", 0o644)

        self.assertFalse((repo / relative).exists())

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
