"""Standalone repository governance and distribution contracts."""

from pathlib import Path
import json
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

    def test_workflow_permissions_are_minimal_and_actions_are_pinned(self):
        self.assertRegex(self.text, r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$")
        self.assertNotRegex(self.text, r"(?mi)^\s+contents:\s*write\s*$")
        self.assertEqual(len(re.findall(r"(?m)^\s+id-token:\s*write\s*$", self.text)), 1)
        self.assertEqual(len(re.findall(r"(?m)^\s+attestations:\s*write\s*$", self.text)), 1)
        uses = re.findall(r"(?m)^\s*-?\s*uses:\s*([^\s#]+)", self.text)
        self.assertGreaterEqual(len(uses), 4)
        for action in uses:
            self.assertRegex(action, r"^[^@\s]+@[0-9a-f]{40}$")

    def test_checkout_fetches_review_history(self):
        checkout = "actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09"
        blocks = self.text.split("- uses: " + checkout)[1:]
        self.assertEqual(len(blocks), 3)
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
        self.assertIn("os: [ubuntu-24.04, macos-14]", self.text)
        self.assertIn("python: ['3.11', '3.12', '3.13', '3.14']", self.text)
        self.assertIn("python-version: ${{ matrix.python }}", self.text)
        self.assertIn("--check-docs", self.text)

    def test_workflow_uses_signed_exact_head_artifact_attestation_gate(self):
        self.assertRegex(self.text, r"actions/attest@[0-9a-f]{40}")
        self.assertIn("git archive", self.text)
        self.assertIn("gh attestation verify", self.text)
        for option in ("--repo", "--signer-workflow", "--source-digest", "--source-ref"):
            self.assertIn(option, self.text)
        self.assertIn('test "$GITHUB_SHA" = "$(git rev-parse HEAD)"', self.text)
        self.assertNotIn("ACTIONS_ID_TOKEN_REQUEST_TOKEN", self.text)
        self.assertNotIn("continue-on-error", self.text)
        self.assertNotRegex(self.text, r"gh attestation verify[^\n]*\|\|\s*true")

    def test_workflow_attests_each_successful_main_push_without_manifest_state_gate(self):
        attestation_job = self.text.split("  attest-exact-head:", 1)[1]
        self.assertIn("if: github.event_name == 'push' && github.ref == 'refs/heads/main'",
                      attestation_job)
        self.assertIn("needs: [unit, linux-integration]", attestation_job)
        self.assertIn("git archive --format=tar --output \"$ATTESTATION_SUBJECT\" HEAD",
                      attestation_job)
        self.assertIn('--source-digest "$GITHUB_SHA"', attestation_job)
        self.assertNotIn("repositoryStatus", attestation_job)
        self.assertNotIn("DELIVERY.json", attestation_job)

    def test_attestation_temp_path_uses_only_step_valid_runner_contexts(self):
        attestation_job = self.text.split("  attest-exact-head:", 1)[1]
        job_header, steps = attestation_job.split("    steps:", 1)
        subject = "${{ runner.temp }}/autonomous-engineering-control.tar"

        self.assertNotIn("ATTESTATION_SUBJECT", job_header)
        self.assertIn("subject-path: " + subject, steps)
        self.assertNotIn("${{ env.ATTESTATION_SUBJECT }}", steps)
        self.assertEqual(steps.count("ATTESTATION_SUBJECT: " + subject), 2)

    def test_macos_python_policy_uses_hosted_toolcache_not_homebrew(self):
        wrapper = (REPO / "scripts/agent-harness").read_text(encoding="utf-8")
        self.assertIn("/Users/runner/hostedtoolcache/Python", wrapper)
        self.assertNotIn("/opt/homebrew", wrapper)

    def test_python_hardening_skips_read_only_toolcache_entries(self):
        hardening = self.text.split("- name: Harden controlled Python", 1)[1].split(
            "- name: Verify controlled Python", 1
        )[0]
        self.assertIn('for path in "${pythonLocation%/*/*}"', hardening)
        self.assertIn('if [[ -w "$path" ]]; then', hardening)
        self.assertIn('chmod go-w "$path"', hardening)
        self.assertNotIn('run: chmod go-w ', hardening)

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
            host = Path(directory).resolve() / "host"
            host.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=host,
                           capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "harness@example.invalid"],
                           cwd=host, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Harness Test"],
                           cwd=host, capture_output=True, check=True)
            (host / "host.txt").write_text("host\n", encoding="utf-8")
            subprocess.run(["git", "add", "host.txt"], cwd=host, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "host fixture"], cwd=host,
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
            self.assertTrue((host / ".agent-harness-install.json").is_file())
            self.assertEqual(policy.read_text(), "host-owned\n")

            duplicate = self.run_script("install.sh", host)
            self.assertEqual(duplicate.returncode, 3)
            upgraded = self.run_script("upgrade.sh", host)
            self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
            self.assertTrue(any((host / ".agent-harness-backups").iterdir()))

            removed = self.run_script("uninstall.sh", host)
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertFalse((host / "scripts/agent-harness").exists())
            self.assertFalse((host / ".agent-harness-install.json").exists())
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

    def test_portable_templates_start_in_a_checkable_pending_state(self):
        for base in (REPO / "templates/host", REPO / "examples/minimal"):
            with self.subTest(base=base):
                delivery = json.loads((base / "docs/agent/HARNESS_DELIVERY.json").read_text())
                self.assertEqual(delivery["deliveryStatus"], "not_started")
                self.assertEqual(delivery["reviewEvidence"]["requiredReviewers"],
                                 ["security", "dx_ci", "whole_branch"])
                self.assertEqual(delivery["reviewEvidence"]["reports"], [])
                for relative in ("AGENTS.md", "docs/agent/AUTONOMY.md",
                                 "docs/agent/PROJECT_MEMORY.md"):
                    self.assertIn("<!-- harness-delivery-status: not_started -->",
                                  (base / relative).read_text())

    def test_minimal_portable_fixture_passes_real_docs_check(self):
        result = subprocess.run([
            str(REPO / "scripts/agent-harness"), "--python",
            "tools/agent-harness/drills/run_drills.py",
            "--repo", "examples/minimal", "--check-docs",
        ], cwd=REPO, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(result.stdout.strip(), "PASS plan-memory-drift")

    def test_minimal_example_baseline_is_an_intentional_red_fixture(self):
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=REPO / "examples/minimal", text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("'ready'", result.stderr)

    def test_portable_protected_paths_cover_root_dependency_and_migration_files(self):
        required = {"migrations/**", "*.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}
        for base in (REPO / "templates/host", REPO / "examples/minimal"):
            with self.subTest(base=base):
                document = json.loads((base / "docs/agent/PROTECTED_PATHS.yaml").read_text())
                patterns = {pattern for rule in document["rules"] for pattern in rule["patterns"]
                            if rule["action"] == "approval_required"}
                self.assertTrue(required <= patterns, required - patterns)

    def test_generic_state_fixture_contains_no_host_project_name(self):
        fixture = REPO / "tools/agent-harness/tests/fixtures/valid_state.json"
        self.assertNotIn("survey", fixture.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
