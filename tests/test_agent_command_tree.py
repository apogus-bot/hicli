import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "bin" / "hi-homeinsight"


class AgentCommandTreeTests(unittest.TestCase):
    def run_cli(self, *args, env=None):
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            [str(CLI), *args],
            cwd=REPO_ROOT,
            env=merged_env,
            text=True,
            capture_output=True,
        )

    def test_help_promotes_agent_facing_top_level_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("help", env={"HI_CONFIG_DIR": tmp})
        self.assertEqual(result.returncode, 0, result.stderr)
        for expected in [
            "profile get | update | avatar-upload | load-area get | load-area set",
            "notifications list | read <ID> | read-all",
            "photos stage | edit | save | manage",
            "packages list | get <ID> | create | update <ID>",
            "analysis start | get | pending | stream | issues",
            "companies me | create | search | invite | requests",
            "team list",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, result.stdout)

    def test_help_omits_blog_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("help", env={"HI_CONFIG_DIR": tmp})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("blog list", result.stdout)
        self.assertNotIn("blog create", result.stdout)


if __name__ == "__main__":
    unittest.main()