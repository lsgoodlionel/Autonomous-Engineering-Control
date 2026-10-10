"""Fail-closed regeneration checks for generated path authorization."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


HARNESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS))

from agent_harness.generated_verifier import (  # noqa: E402
    generated_binding_is_current,
    verify_generated_outputs,
)
from agent_harness.git_guard import PathDecision  # noqa: E402


class GeneratedVerifierTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name).resolve() / "repo"
        self.repo.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Harness Test")
        self.write(".gitignore", "/var/agent-harness/\n")
        self.write("inputs/source.txt", "bound input\n")
        self.write("tools/render.py", (
            "from pathlib import Path\n"
            "source = Path('inputs/source.txt').read_bytes()\n"
            "target = Path('generated/output.md')\n"
            "target.parent.mkdir(parents=True, exist_ok=True)\n"
            "target.write_bytes(b'# generated\\n' + source)\n"
        ))
        self.write("generated/output.md", "# generated\nbound input\n")
        self.git("add", ".")
        self.git("commit", "-m", "fixture")
        self.evidence = self.repo / "var/agent-harness/runs/test/evidence/generated"

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, relative, content):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def decision(self, command=None):
        return PathDecision(
            "generated/output.md", "generated", ("generated-output",), "policy_rule",
            tuple(command or (sys.executable, "tools/render.py")),
        )

    def verify(self, *decisions, timeout=2):
        return verify_generated_outputs(
            self.repo, decisions or (self.decision(),), self.evidence,
            timeout_seconds=timeout,
        )

    def metadata(self, result):
        return json.loads((self.repo / result.metadata_path).read_text(encoding="utf-8"))

    def test_exact_regeneration_passes_and_binds_inputs_outputs_and_argv(self):
        result, = self.verify()

        self.assertTrue(result.passed)
        self.assertIsNone(result.failure_kind)
        self.assertTrue(generated_binding_is_current(self.repo, result.binding))
        metadata = self.metadata(result)
        self.assertEqual(metadata["status"], "passed")
        self.assertEqual(metadata["command"], [sys.executable, "tools/render.py"])
        self.assertEqual(metadata["outputs"], ["generated/output.md"])
        self.assertRegex(metadata["inputSha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(metadata["outputSha256"]["generated/output.md"], r"^[0-9a-f]{64}$")

    def test_survey_capabilities_generator_argv_shape_is_executed_without_shell(self):
        self.write("platform/docs/productization/capabilities.json", '{"title":"能力"}\n')
        self.write("platform/tools/productization/render_capabilities.py", (
            "import json\n"
            "from pathlib import Path\n"
            "data = json.loads(Path('platform/docs/productization/capabilities.json').read_text())\n"
            "Path('platform/docs/productization/capability-map.md').write_text('# ' + data['title'] + '\\n')\n"
        ))
        self.write("platform/docs/productization/capability-map.md", "# 能力\n")
        self.git("add", ".")
        self.git("commit", "-m", "survey shape")
        decision = PathDecision(
            "platform/docs/productization/capability-map.md", "generated",
            ("capability-map",), "policy_rule",
            ("python3", "platform/tools/productization/render_capabilities.py"),
        )

        result, = self.verify(decision)

        self.assertTrue(result.passed, self.metadata(result))
        self.assertEqual(self.metadata(result)["command"], [
            "python3", "platform/tools/productization/render_capabilities.py",
        ])
        self.assertFalse((self.repo / "injected").exists())

    def test_output_byte_mismatch_is_rejected_with_diagnostic(self):
        self.write("generated/output.md", "hand edited\n")

        result, = self.verify()

        self.assertFalse(result.passed)
        self.assertEqual(result.failure_kind, "output_mismatch")
        self.assertEqual(self.metadata(result)["failureKind"], "output_mismatch")

    def test_out_of_scope_workspace_write_is_rejected(self):
        self.write("tools/render.py", (
            "from pathlib import Path\n"
            "Path('generated').mkdir(exist_ok=True)\n"
            "Path('generated/output.md').write_text('# generated\\nbound input\\n')\n"
            "Path('unexpected.txt').write_text('escape')\n"
        ))

        result, = self.verify()

        self.assertFalse(result.passed)
        self.assertEqual(result.failure_kind, "out_of_scope_write")
        self.assertEqual(self.metadata(result)["unexpectedPaths"], ["unexpected.txt"])
        self.assertFalse((self.repo / "unexpected.txt").exists())

    def test_parent_workspace_write_is_rejected(self):
        self.write("tools/render.py", (
            "from pathlib import Path\n"
            "Path('generated').mkdir(exist_ok=True)\n"
            "Path('generated/output.md').write_text('# generated\\nbound input\\n')\n"
            "Path('../escaped.txt').write_text('escape')\n"
        ))

        result, = self.verify()

        self.assertFalse(result.passed)
        self.assertEqual(result.failure_kind, "out_of_scope_write")
        self.assertIn("../escaped.txt", self.metadata(result)["unexpectedPaths"])

    def test_home_and_temp_scratch_is_contained_inside_the_isolation_boundary(self):
        external_home = self.repo.parent / "external-home"
        external_temp = self.repo.parent / "external-temp"
        external_home.mkdir()
        external_temp.mkdir()
        self.write("tools/render.py", (
            "import os\n"
            "from pathlib import Path\n"
            "Path('generated').mkdir(exist_ok=True)\n"
            "Path('generated/output.md').write_text('# generated\\nbound input\\n')\n"
            "(Path.home() / 'escaped-home.txt').write_text('escape')\n"
            "(Path(os.environ['TMPDIR']) / 'escaped-temp.txt').write_text('escape')\n"
        ))

        with patch.dict(os.environ, {
            "HOME": str(external_home),
            "TMPDIR": str(external_temp),
            "TMP": str(external_temp),
            "TEMP": str(external_temp),
        }):
            result, = self.verify()

        self.assertTrue(result.passed, self.metadata(result))
        self.assertFalse((external_home / "escaped-home.txt").exists())
        self.assertFalse((external_temp / "escaped-temp.txt").exists())

    def test_missing_executable_and_missing_registered_script_are_rejected(self):
        cases = (
            (("absent-generator-tool-96b36b",), "missing_executable"),
            ((sys.executable, "tools/missing.py"), "missing_generator"),
        )
        for command, expected in cases:
            with self.subTest(command=command):
                result, = self.verify(self.decision(command))
                self.assertFalse(result.passed)
                self.assertEqual(result.failure_kind, expected)

    def test_timeout_kills_generator_and_records_typed_failure(self):
        self.write("tools/render.py", "import time\ntime.sleep(30)\n")

        result, = self.verify(timeout=1)

        self.assertFalse(result.passed)
        self.assertEqual(result.failure_kind, "timeout")
        self.assertEqual(self.metadata(result)["failureKind"], "timeout")

    def test_bound_input_or_output_change_invalidates_prior_binding(self):
        result, = self.verify()
        self.assertTrue(generated_binding_is_current(self.repo, result.binding))

        self.write("inputs/source.txt", "drifted input\n")
        self.assertFalse(generated_binding_is_current(self.repo, result.binding))
        self.write("inputs/source.txt", "bound input\n")
        self.write("generated/output.md", "drifted output\n")
        self.assertFalse(generated_binding_is_current(self.repo, result.binding))

    def test_concurrent_source_input_change_is_rejected_as_input_mismatch(self):
        from agent_harness import generated_verifier as module
        stop_process = module._stop_process

        def drift_input(process):
            stop_process(process)
            self.write("inputs/source.txt", "concurrent drift\n")

        with patch.object(module, "_stop_process", side_effect=drift_input):
            result, = self.verify()

        self.assertFalse(result.passed)
        self.assertEqual(result.failure_kind, "input_mismatch")
        self.assertEqual(self.metadata(result)["failureKind"], "input_mismatch")

    def test_shell_metacharacters_in_argv_remain_literal(self):
        marker = "$(touch injected)"
        self.write("tools/argv.py", (
            "from pathlib import Path\n"
            "import sys\n"
            "Path('generated').mkdir(exist_ok=True)\n"
            "Path('generated/output.md').write_text(sys.argv[1] + '\\n')\n"
        ))
        self.write("generated/output.md", marker + "\n")

        result, = self.verify(self.decision((sys.executable, "tools/argv.py", marker)))

        self.assertTrue(result.passed)
        self.assertFalse((self.repo / "injected").exists())

    def test_git_input_paths_with_newlines_are_bound_without_line_splitting(self):
        unusual = "inputs/line\nbreak.txt"
        self.write(unusual, "newline path input\n")
        self.git("add", unusual)
        self.git("commit", "-m", "newline input")

        result, = self.verify()

        self.assertTrue(result.passed, self.metadata(result))
        self.write(unusual, "drifted newline path input\n")
        self.assertFalse(generated_binding_is_current(self.repo, result.binding))


if __name__ == "__main__":
    unittest.main()
