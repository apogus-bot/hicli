import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "weekly" / "run_weekly.py"
spec = importlib.util.spec_from_file_location("homeinsight_weekly", MODULE_PATH)
weekly = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(weekly)


class WeeklyRunnerSecurityTests(unittest.TestCase):
    def test_write_json_locks_file_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "runs" / "state.json"
            weekly.write_json(target, {"ok": True})
            file_mode = stat.S_IMODE(target.stat().st_mode)
            dir_mode = stat.S_IMODE(target.parent.stat().st_mode)
        self.assertEqual(file_mode, 0o600)
        self.assertEqual(dir_mode, 0o700)

    def test_append_jsonl_locks_file_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "logs" / "weekly.jsonl"
            weekly.append_jsonl(target, {"run": 1})
            file_mode = stat.S_IMODE(target.stat().st_mode)
            dir_mode = stat.S_IMODE(target.parent.stat().st_mode)
            content = target.read_text(encoding="utf-8")
        self.assertEqual(file_mode, 0o600)
        self.assertEqual(dir_mode, 0o700)
        self.assertIn('"run": 1', content)

    def test_session_snapshot_omits_sensitive_path_and_user_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            session_path = Path(tmp) / "session.json"
            session_path.write_text(
                json.dumps(
                    {
                        "email": "agent@example.com",
                        "user_id": "user-123",
                        "expires_at": 4102444800,
                        "access_token": "a",
                        "refresh_token": "b",
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(weekly, "SESSION_PATH", session_path):
                snapshot = weekly.session_snapshot()
        self.assertNotIn("path", snapshot)
        self.assertNotIn("user_id", snapshot)
        self.assertEqual(snapshot["email"], "agent@example.com")
        self.assertTrue(snapshot["has_access_token"])
        self.assertTrue(snapshot["has_refresh_token"])

    def test_run_command_redacts_stdio_in_command_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            completed = mock.Mock(returncode=0, stdout='{"ok":true}\n', stderr='warning\n')
            with mock.patch.object(weekly.subprocess, "run", return_value=completed):
                record = weekly.run_command(["echo", "hi"], run_dir, "demo")
            saved = json.loads((run_dir / "demo.command.json").read_text(encoding="utf-8"))
        self.assertEqual(record["returncode"], 0)
        self.assertNotIn("stdout", saved)
        self.assertNotIn("stderr", saved)
        self.assertEqual(saved["stdout_bytes"], len(completed.stdout.encode("utf-8")))
        self.assertEqual(saved["stderr_bytes"], len(completed.stderr.encode("utf-8")))

    def test_ensure_auth_ready_redacts_stdio_in_command_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            completed = mock.Mock(returncode=0, stdout='{"expired": false}\n', stderr='')
            with mock.patch.object(weekly.subprocess, "run", return_value=completed):
                with mock.patch.object(weekly, "session_snapshot", side_effect=[{"exists": True}, {"exists": True}]):
                    payload = weekly.ensure_auth_ready(run_dir)
            saved = json.loads((run_dir / "auth_preflight.command.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["expired"], False)
        self.assertNotIn("stdout", saved)
        self.assertNotIn("stderr", saved)
        self.assertEqual(saved["stdout_bytes"], len(completed.stdout.encode("utf-8")))


if __name__ == "__main__":
    unittest.main()
