import json
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


class BlogPayloadTests(unittest.TestCase):
    def test_build_blog_create_payload_without_helper_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            content_file = Path(tmp) / "post.md"
            content_file.write_text("# Hello\nWorld\n", encoding="utf-8")
            shell = textwrap.dedent(
                f'''
                set -euo pipefail
                {SOURCE_PREFIX}
                build_blog_create_payload \
                  --title "My Post" \
                  --content-file "{content_file}" \
                  --slug "my-post" \
                  --excerpt "short" \
                  --tags '["one","two"]' \
                  --meta-title "Meta" \
                  --meta-description "Desc" \
                  --featured-image-url "https://example.com/img.png"
                '''
            )
            result = subprocess.run(["bash", "-lc", shell], cwd=REPO_ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["title"], "My Post")
        self.assertEqual(payload["slug"], "my-post")
        self.assertEqual(payload["tags"], ["one", "two"])
        self.assertIn("World", payload["content"])


if __name__ == "__main__":
    unittest.main()
