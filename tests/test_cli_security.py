import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "bin" / "hi-homeinsight"
SOURCE_PREFIX = textwrap.dedent(
    r'''
    source <(sed '/^case "${1:-help}" in/,$d' "__CLI__")
    '''
).strip().replace("__CLI__", str(CLI))


class HomeInsightCliSecurityTests(unittest.TestCase):
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

    def test_default_help_omits_admin_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("help", env={"HI_CONFIG_DIR": tmp})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("stats                               Admin dashboard stats", result.stdout)
        self.assertNotIn("api METHOD /path [--data JSON]", result.stdout)
        self.assertNotIn("sync status | logs | run", result.stdout)

    def test_admin_command_blocked_without_enable_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("stats", env={"HI_CONFIG_DIR": tmp})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HI_ENABLE_ADMIN=1", result.stderr)

    def test_admin_help_visible_with_enable_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("help", env={"HI_CONFIG_DIR": tmp, "HI_ENABLE_ADMIN": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("stats                               Admin dashboard stats", result.stdout)
        self.assertIn("api METHOD /path [--data JSON]", result.stdout)

    def test_help_locks_config_dir_permissions(self):
        with tempfile.TemporaryDirectory() as tmp_parent:
            config_dir = Path(tmp_parent) / "config"
            result = self.run_cli("help", env={"HI_CONFIG_DIR": str(config_dir)})
            self.assertEqual(result.returncode, 0, result.stderr)
            mode = stat.S_IMODE(config_dir.stat().st_mode)
        self.assertEqual(mode, 0o700)

    def test_auth_status_does_not_expose_auth_env_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth_env = Path(tmp) / "auth.env"
            auth_env.write_text('HI_EMAIL="user@example.com"\n')
            os.chmod(auth_env, 0o600)
            session = Path(tmp) / "session.json"
            session.write_text(json.dumps({"email": "user@example.com", "expires_at": 4102444800}))
            os.chmod(session, 0o600)
            result = self.run_cli(
                "auth",
                "status",
                env={"HI_CONFIG_DIR": tmp, "HI_AUTH_ENV_FILE": str(auth_env)},
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertNotIn("auth_env_file", payload)
        self.assertTrue(payload["auth_env_file_present"])

    def test_login_rejects_password_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(
                "login",
                "--email",
                "user@example.com",
                "--password",
                "secret123",
                env={"HI_CONFIG_DIR": tmp},
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HI_PASSWORD", result.stderr)
        self.assertIn("--password", result.stderr)

    def test_secure_file_helper_locks_file_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_file = Path(tmp) / "session.json"
            temp_file.write_text(json.dumps({"ok": True}))
            os.chmod(temp_file, 0o644)
            shell = textwrap.dedent(
                f'''
                set -euo pipefail
                {SOURCE_PREFIX}
                secure_file "{temp_file}"
                stat -c %a "{temp_file}"
                '''
            )
            result = subprocess.run(
                ["bash", "-lc", shell],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "600")


if __name__ == "__main__":
    unittest.main()
