"""Standalone repository governance and distribution contracts."""

from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[3]
WORKFLOW = REPO / ".github/workflows/ci.yml"


class GovernanceWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_is_read_only_and_pinned(self):
        self.assertRegex(self.text, r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$")
        self.assertNotRegex(self.text, r"(?mi)^\s*[a-z-]+:\s*write\s*$")
        uses = re.findall(r"(?m)^\s*-?\s*uses:\s*([^\s#]+)", self.text)
        self.assertGreaterEqual(len(uses), 4)
        for action in uses:
            self.assertRegex(action, r"^[^@\s]+@[0-9a-f]{40}$")

    def test_checkout_fetches_review_history(self):
        checkout = "actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09"
        blocks = self.text.split("- uses: " + checkout)[1:]
        self.assertEqual(len(blocks), 2)
        for block in blocks:
            self.assertRegex(block, r"(?m)^\s+with:\s*\n\s+fetch-depth:\s*0\s*$")

    def test_workflow_uses_controlled_python_and_zero_skip_linux_fixture(self):
        image = ("python:3.11-slim@sha256:"
                 "e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce")
        self.assertIn("AGENT_HARNESS_CI: '1'", self.text)
        self.assertIn("scripts/agent-harness --python --version", self.text)
        self.assertIn("--exclude-substring linux_wrapper --fail-on-skip", self.text)
        self.assertIn("--include-substring linux_wrapper --fail-on-skip --ci", self.text)
        self.assertIn("--linux-image " + image, self.text)
        self.assertIn("--docker /usr/bin/docker", self.text)
        harden = ('chmod go-w /opt/hostedtoolcache/Python "${pythonLocation%/*}" '
                  '"$pythonLocation" "$pythonLocation/bin" "$pythonLocation/bin/python3.11"')
        self.assertEqual(self.text.count(harden), 2)

    def test_workflow_has_no_delivery_side_effects(self):
        for pattern in (r"\bgit\s+push\b", r"\bgh\s+release\b", r"\bdeploy(?:ment)?\b",
                        r"pull-requests:\s*write", r"packages:\s*write"):
            self.assertNotRegex(self.text.lower(), pattern)

    def test_ci_test_runner_fails_on_skip_and_partitions(self):
        runner = REPO / "tools/agent-harness/run_tests.py"
        with tempfile.TemporaryDirectory() as directory:
            test_file = Path(directory) / "test_partition.py"
            test_file.write_text(
                "import unittest\n"
                "class Partition(unittest.TestCase):\n"
                " def test_unit(self): pass\n"
                " @unittest.skip('fixture missing')\n"
                " def test_linux_wrapper_fixture(self): pass\n",
                encoding="utf-8",
            )
            unit = subprocess.run([
                sys.executable, str(runner), "--start-directory", directory,
                "--exclude-substring", "linux_wrapper", "--fail-on-skip",
            ], text=True, capture_output=True, check=False)
            integration = subprocess.run([
                sys.executable, str(runner), "--start-directory", directory,
                "--include-substring", "linux_wrapper", "--fail-on-skip",
            ], text=True, capture_output=True, check=False)
        self.assertEqual(unit.returncode, 0, unit.stdout + unit.stderr)
        self.assertEqual(integration.returncode, 2, integration.stdout + integration.stderr)


class DistributionTests(unittest.TestCase):
    def run_script(self, name, target):
        return subprocess.run([str(REPO / name), str(target)], cwd=REPO,
                              text=True, capture_output=True, check=False,
                              env={**os.environ, "TZ": "UTC"})

    def test_install_upgrade_and_uninstall_preserve_host_state(self):
        with tempfile.TemporaryDirectory() as directory:
            host = Path(directory) / "host"
            host.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=host,
                           capture_output=True, check=True)
            policy = host / "docs/agent/PROJECT_MEMORY.md"
            policy.parent.mkdir(parents=True)
            policy.write_text("host-owned\n", encoding="utf-8")
            history = host / "var/agent-harness/keep.txt"
            history.parent.mkdir(parents=True)
            history.write_text("evidence\n", encoding="utf-8")

            installed = self.run_script("install.sh", host)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            self.assertTrue((host / "scripts/agent-harness").is_file())
            self.assertTrue((host / ".agent-harness-install").is_file())
            self.assertEqual(policy.read_text(), "host-owned\n")

            duplicate = self.run_script("install.sh", host)
            self.assertEqual(duplicate.returncode, 3)
            upgraded = self.run_script("upgrade.sh", host)
            self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
            self.assertTrue(any((host / ".agent-harness-backups").iterdir()))

            removed = self.run_script("uninstall.sh", host)
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertFalse((host / "scripts/agent-harness").exists())
            self.assertFalse((host / ".agent-harness-install").exists())
            self.assertEqual(policy.read_text(), "host-owned\n")
            self.assertEqual(history.read_text(), "evidence\n")

    def test_distribution_contains_no_host_product_names(self):
        forbidden = re.compile(r"LimeSurvey|MjyRuntime|star-survey|platform/tools/productization")
        roots = (REPO / "scripts", REPO / "tools/agent-harness/agent_harness",
                 REPO / "docs/agent", REPO / "install.sh", REPO / "upgrade.sh",
                 REPO / "uninstall.sh")
        for root in roots:
            files = (root,) if root.is_file() else tuple(root.rglob("*"))
            for path in files:
                if path.is_file() and path.suffix in ("", ".py", ".json", ".md", ".sh"):
                    self.assertIsNone(forbidden.search(path.read_text(encoding="utf-8")), path)


if __name__ == "__main__":
    unittest.main()
