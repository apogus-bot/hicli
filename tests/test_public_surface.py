import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
ACTION_SURFACE = REPO_ROOT / "docs" / "va-action-surface.md"
CLI = REPO_ROOT / "bin" / "hi-homeinsight"


class PublicSurfaceTests(unittest.TestCase):
    def test_public_docs_omit_admin_internal_section(self):
        action_surface = ACTION_SURFACE.read_text(encoding="utf-8")
        self.assertNotIn("## Admin / internal actions", action_surface)
        self.assertNotIn("raw authenticated API escape hatch", action_surface)
        self.assertNotIn("admin dashboard stats", action_surface)

    def test_readme_omits_admin_enablement_language(self):
        readme = README.read_text(encoding="utf-8")
        self.assertNotIn("## Admin commands", readme)
        self.assertNotIn("Only enable them for trusted internal workflows", readme)

    def test_public_cli_source_omits_admin_helpers_and_markers(self):
        cli = CLI.read_text(encoding="utf-8")
        forbidden = [
            "ADMIN COMMANDS",
            "admin-only",
            "blog?admin=true",
            "/admin/",
            "cmd_stats()",
            "cmd_users()",
            "cmd_agents()",
            "cmd_ai()",
            "cmd_sync()",
            "cmd_health()",
            "cmd_api()",
        ]
        for item in forbidden:
            with self.subTest(item=item):
                self.assertNotIn(item, cli)


if __name__ == "__main__":
    unittest.main()
