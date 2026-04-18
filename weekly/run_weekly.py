#!/usr/bin/env python3
import argparse
import html
import json
import os
import re
import subprocess
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ORIGIN = os.environ.get("HI_APP", "https://www.homeinsightai.com")
HI_CLI = Path(os.environ.get("HI_CLI_BIN", str(REPO_ROOT / "bin" / "hi-homeinsight")))
DEFAULT_LOG_PATH = REPO_ROOT / "logs" / "homeinsight-weekly-runs.jsonl"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "weekly" / "runs"
SESSION_PATH = Path(os.environ.get("HI_CONFIG_DIR", str(Path.home() / ".config/hi-cli-homeinsight"))) / "session.json"


class WeeklyRunError(Exception):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"^-+|-+$", "", value)
    return value or "weekly-homeinsight-update"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def append_jsonl(path: Path, data: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, sort_keys=True) + "\n")


def resolve_path(base_dir: Path, maybe_path: Optional[str]) -> Optional[Path]:
    if not maybe_path:
        return None
    path = Path(maybe_path)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def read_json_file(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise WeeklyRunError(f"Manifest not found: {path}")
    except json.JSONDecodeError as exc:
        raise WeeklyRunError(f"Manifest is not valid JSON: {exc}")


def load_manifest(path: Path) -> Dict[str, Any]:
    manifest = read_json_file(path)
    base_dir = path.parent.resolve()

    blog = manifest.setdefault("blog", {})
    email_cfg = manifest.setdefault("email", {})
    run_cfg = manifest.setdefault("run", {})

    title = (blog.get("title") or "").strip()
    if not title:
        raise WeeklyRunError("Manifest requires blog.title")

    content_file = resolve_path(base_dir, blog.get("content_file"))
    if not content_file or not content_file.exists():
        raise WeeklyRunError("Manifest requires blog.content_file that exists")

    blog["content_file"] = str(content_file)
    blog.setdefault("slug", slugify(title))
    blog.setdefault("tags", [])
    blog.setdefault("excerpt", "")
    blog.setdefault("meta_title", blog.get("title", ""))
    blog.setdefault("meta_description", blog.get("excerpt", ""))
    blog.setdefault("featured_image_url", "")
    blog.setdefault("live_url", "")

    output_root = resolve_path(base_dir, run_cfg.get("output_root")) or DEFAULT_OUTPUT_ROOT
    run_cfg["output_root"] = str(output_root)
    run_cfg.setdefault("create_or_update", True)
    run_cfg.setdefault("publish", True)
    run_cfg.setdefault("generate_email_package", True)
    run_cfg.setdefault("update_blog_email_fields", True)
    run_cfg.setdefault("send_test", True)

    email_cfg.setdefault("subject", blog.get("title", ""))
    email_cfg.setdefault("preheader", blog.get("excerpt", ""))
    email_cfg.setdefault("headline", blog.get("title", ""))
    email_cfg.setdefault("cta_label", "Read the full post")
    email_cfg.setdefault("intro_html", "")
    email_cfg.setdefault("closing_html", "")
    email_cfg.setdefault("key_points", [])
    email_cfg.setdefault("from", "")

    return manifest


def session_snapshot() -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {"exists": SESSION_PATH.exists(), "path": str(SESSION_PATH)}
    if not SESSION_PATH.exists():
        snapshot["expired"] = True
        snapshot["has_password_env"] = bool(os.environ.get("HI_PASSWORD"))
        return snapshot
    try:
        data = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    except Exception:
        snapshot["expired"] = True
        snapshot["read_error"] = True
        snapshot["has_password_env"] = bool(os.environ.get("HI_PASSWORD"))
        return snapshot

    expires_at = data.get("expires_at")
    snapshot["email"] = data.get("email")
    snapshot["user_id"] = data.get("user_id")
    snapshot["expires_at"] = expires_at
    snapshot["has_access_token"] = bool(data.get("access_token"))
    snapshot["has_refresh_token"] = bool(data.get("refresh_token"))
    expired = True
    if isinstance(expires_at, int):
        expired = expires_at <= int(now_utc().timestamp())
    snapshot["expired"] = expired
    snapshot["has_password_env"] = bool(os.environ.get("HI_PASSWORD"))
    return snapshot


def ensure_auth_ready(run_dir: Path) -> Dict[str, Any]:
    command_args = [str(HI_CLI), "auth", "ensure"]
    session_before = session_snapshot()
    result = subprocess.run(command_args, capture_output=True, text=True)
    command_record = {
        "args": command_args,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "session_before": session_before,
    }
    if result.returncode == 0:
        command_record["session_after"] = session_snapshot()
    write_json(run_dir / "auth_preflight.command.json", command_record)

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "command failed").strip()
        raise WeeklyRunError(
            "HomeInsight CLI auth preflight failed. Automatic refresh/login did not succeed. "
            f"Run hi-homeinsight-dev auth ensure manually to inspect the issue. Details: {err}"
        )

    try:
        payload = parse_json_output(result.stdout)
        if isinstance(payload, dict):
            write_json(run_dir / "auth_preflight.response.json", payload)
            return payload
    except WeeklyRunError:
        pass

    snapshot = session_snapshot()
    write_json(run_dir / "auth_preflight.response.json", snapshot)
    return snapshot


def run_command(args: List[str], run_dir: Path, step_name: str) -> Dict[str, Any]:
    result = subprocess.run(args, capture_output=True, text=True)
    command_record = {
        "args": args,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    write_json(run_dir / f"{step_name}.command.json", command_record)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "command failed").strip()
        raise WeeklyRunError(f"{step_name} failed: {err}")
    return command_record


def parse_json_output(raw: str) -> Any:
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise WeeklyRunError("Expected JSON output from HomeInsight CLI but could not parse it.")


def unwrap_post(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        for key in ("post", "blog", "data"):
            if isinstance(payload.get(key), dict):
                return payload[key]
        if "id" in payload:
            return payload
        if isinstance(payload.get("posts"), list) and payload["posts"]:
            first = payload["posts"][0]
            if isinstance(first, dict):
                return first
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    raise WeeklyRunError("HomeInsight CLI returned JSON, but no blog post record could be extracted.")


def public_get_json(url: str) -> Any:
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")
        raise WeeklyRunError(f"Public fetch failed for {url}: {body or exc.reason}")
    except Exception as exc:
        raise WeeklyRunError(f"Public fetch failed for {url}: {exc}")


def fetch_public_post(id_or_slug: str) -> Dict[str, Any]:
    payload = public_get_json(f"{APP_ORIGIN}/api/blog/{urllib.parse.quote(id_or_slug)}")
    return unwrap_post(payload)


def create_or_update_blog(manifest: Dict[str, Any], run_dir: Path) -> Dict[str, Any]:
    blog = manifest["blog"]
    args = [str(HI_CLI), "blog"]
    if blog.get("id"):
        args += ["update", str(blog["id"]), "--title", blog["title"], "--content-file", blog["content_file"]]
        if blog.get("slug"):
            args += ["--slug", blog["slug"]]
        if blog.get("excerpt"):
            args += ["--excerpt", blog["excerpt"]]
        if blog.get("tags"):
            args += ["--tags", json.dumps(blog["tags"])]
        if blog.get("meta_title"):
            args += ["--meta-title", blog["meta_title"]]
        if blog.get("meta_description"):
            args += ["--meta-description", blog["meta_description"]]
        if blog.get("featured_image_url"):
            args += ["--featured-image-url", blog["featured_image_url"]]
        step = "blog_update"
    else:
        args += ["create", "--title", blog["title"], "--content-file", blog["content_file"]]
        if blog.get("slug"):
            args += ["--slug", blog["slug"]]
        if blog.get("excerpt"):
            args += ["--excerpt", blog["excerpt"]]
        if blog.get("tags"):
            args += ["--tags", json.dumps(blog["tags"])]
        if blog.get("meta_title"):
            args += ["--meta-title", blog["meta_title"]]
        if blog.get("meta_description"):
            args += ["--meta-description", blog["meta_description"]]
        if blog.get("featured_image_url"):
            args += ["--featured-image-url", blog["featured_image_url"]]
        step = "blog_create"

    record = run_command(args, run_dir, step)
    payload = parse_json_output(record["stdout"])
    post = unwrap_post(payload)
    write_json(run_dir / f"{step}.response.json", payload)
    return post


def publish_blog(post: Dict[str, Any], run_dir: Path) -> Dict[str, Any]:
    blog_id = post.get("id")
    if not blog_id:
        raise WeeklyRunError("Cannot publish blog without blog id.")
    record = run_command([str(HI_CLI), "blog", "publish", str(blog_id)], run_dir, "blog_publish")
    payload = parse_json_output(record["stdout"])
    write_json(run_dir / "blog_publish.response.json", payload)
    try:
        published_post = unwrap_post(payload)
    except WeeklyRunError:
        published_post = dict(post)
    merged = dict(post)
    merged.update(published_post)
    return merged


def resolve_live_url(post: Dict[str, Any], manifest: Dict[str, Any]) -> str:
    if post.get("slug"):
        return f"{APP_ORIGIN}/blog/{post['slug']}"
    if manifest["blog"].get("live_url"):
        return manifest["blog"]["live_url"]
    if manifest["blog"].get("slug"):
        return f"{APP_ORIGIN}/blog/{manifest['blog']['slug']}"
    if post.get("id"):
        try:
            public_post = fetch_public_post(str(post["id"]))
            if public_post.get("slug"):
                return f"{APP_ORIGIN}/blog/{public_post['slug']}"
        except WeeklyRunError:
            pass
    raise WeeklyRunError("Could not determine live blog URL after publish.")


def build_email_html(manifest: Dict[str, Any], live_url: str) -> str:
    blog = manifest["blog"]
    email_cfg = manifest["email"]
    title = html.escape(email_cfg.get("headline") or blog["title"])
    preheader = html.escape(email_cfg.get("preheader") or blog.get("excerpt") or blog["title"])
    excerpt = html.escape(blog.get("excerpt") or "See what HomeInsight shipped this week and why it matters for agents.")
    cta_label = html.escape(email_cfg.get("cta_label") or "Read the full post")
    intro_html = email_cfg.get("intro_html") or f"<p style=\"margin:0 0 16px 0;\">{excerpt}</p>"
    closing_html = email_cfg.get("closing_html") or "<p style=\"margin:0;\">– HomeInsight AI</p>"
    points = email_cfg.get("key_points") or []
    points_html = ""
    if points:
        items = "".join(
            f"<li style=\"margin:0 0 8px 0;\">{html.escape(str(item))}</li>" for item in points
        )
        points_html = f"<ul style=\"margin:0 0 24px 20px; padding:0; color:#334155;\">{items}</ul>"

    return textwrap.dedent(
        f"""\
        <!doctype html>
        <html>
          <head>
            <meta charset=\"utf-8\" />
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
            <title>{title}</title>
          </head>
          <body style=\"margin:0; padding:0; background:#f8fafc; font-family:Arial,Helvetica,sans-serif; color:#0f172a;\">
            <div style=\"display:none; max-height:0; overflow:hidden; opacity:0;\">{preheader}</div>
            <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"background:#f8fafc; padding:24px 0;\">
              <tr>
                <td align=\"center\">
                  <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:640px; background:#ffffff; border-radius:16px; overflow:hidden;\">
                    <tr>
                      <td style=\"padding:40px 32px 16px 32px; background:#0f172a; color:#ffffff;\">
                        <div style=\"font-size:12px; letter-spacing:.08em; text-transform:uppercase; opacity:.75; margin-bottom:12px;\">HomeInsight AI Weekly</div>
                        <h1 style=\"margin:0; font-size:30px; line-height:1.2;\">{title}</h1>
                      </td>
                    </tr>
                    <tr>
                      <td style=\"padding:32px; font-size:16px; line-height:1.6;\">
                        {intro_html}
                        {points_html}
                        <p style=\"margin:0 0 24px 0;\">
                          <a href=\"{html.escape(live_url)}\" style=\"display:inline-block; background:#2563eb; color:#ffffff; text-decoration:none; padding:14px 22px; border-radius:999px; font-weight:bold;\">{cta_label}</a>
                        </p>
                        <p style=\"margin:0 0 24px 0; color:#475569;\">If the button doesn’t work, copy and paste this link:<br /><a href=\"{html.escape(live_url)}\">{html.escape(live_url)}</a></p>
                        {closing_html}
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """
    ).strip() + "\n"


def build_email_text(manifest: Dict[str, Any], live_url: str) -> str:
    blog = manifest["blog"]
    email_cfg = manifest["email"]
    lines = [email_cfg.get("headline") or blog["title"], ""]
    if blog.get("excerpt"):
        lines.extend([blog["excerpt"], ""])
    for point in email_cfg.get("key_points") or []:
        lines.append(f"- {point}")
    if email_cfg.get("key_points"):
        lines.append("")
    lines.extend([
        f"Read the full post: {live_url}",
        "",
        "- HomeInsight AI",
    ])
    return "\n".join(lines).strip() + "\n"


def write_email_package(manifest: Dict[str, Any], run_dir: Path, post: Dict[str, Any], live_url: str) -> Dict[str, Any]:
    email_dir = run_dir / "email_package"
    ensure_dir(email_dir)
    html_body = build_email_html(manifest, live_url)
    text_body = build_email_text(manifest, live_url)
    html_path = email_dir / "email.html"
    text_path = email_dir / "email.txt"
    meta_path = email_dir / "email_package.json"
    html_path.write_text(html_body, encoding="utf-8")
    text_path.write_text(text_body, encoding="utf-8")
    metadata = {
        "generated_at": now_iso(),
        "blog_id": post.get("id"),
        "blog_slug": post.get("slug") or manifest["blog"].get("slug"),
        "live_url": live_url,
        "subject": manifest["email"].get("subject") or manifest["blog"]["title"],
        "from": manifest["email"].get("from") or None,
        "files": {
            "html": str(html_path),
            "text": str(text_path),
        },
    }
    write_json(meta_path, metadata)
    return metadata


def update_blog_email_fields(manifest: Dict[str, Any], post: Dict[str, Any], run_dir: Path, email_package: Dict[str, Any]) -> Dict[str, Any]:
    blog_id = post.get("id")
    if not blog_id:
        raise WeeklyRunError("Cannot update blog email fields without blog id.")
    args = [
        str(HI_CLI),
        "blog",
        "update",
        str(blog_id),
        "--email-html-file",
        email_package["files"]["html"],
        "--email-subject",
        manifest["email"].get("subject") or manifest["blog"]["title"],
    ]
    record = run_command(args, run_dir, "blog_update_email")
    payload = parse_json_output(record["stdout"])
    write_json(run_dir / "blog_update_email.response.json", payload)
    merged = dict(post)
    try:
        merged.update(unwrap_post(payload))
    except WeeklyRunError:
        pass
    return merged


def send_test_email(manifest: Dict[str, Any], post: Dict[str, Any], run_dir: Path, email_package: Dict[str, Any]) -> Dict[str, Any]:
    blog_id = post.get("id")
    if not blog_id:
        raise WeeklyRunError("Cannot send test email without blog id.")
    args = [
        str(HI_CLI),
        "blog",
        "send-test",
        str(blog_id),
        "--subject",
        manifest["email"].get("subject") or manifest["blog"]["title"],
        "--email-html-file",
        email_package["files"]["html"],
    ]
    if manifest["email"].get("from"):
        args += ["--from", manifest["email"]["from"]]
    record = run_command(args, run_dir, "blog_send_test")
    payload = parse_json_output(record["stdout"])
    write_json(run_dir / "blog_send_test.response.json", payload)
    return payload if isinstance(payload, dict) else {"result": payload}


def maybe_fetch_public_post(post: Dict[str, Any], run_dir: Path) -> Optional[Dict[str, Any]]:
    token = post.get("slug") or post.get("id")
    if not token:
        return None
    try:
        payload = public_get_json(f"{APP_ORIGIN}/api/blog/{urllib.parse.quote(str(token))}")
        write_json(run_dir / "public_blog_lookup.response.json", payload)
        return unwrap_post(payload)
    except Exception:
        return None


def execute_run(manifest: Dict[str, Any], manifest_path: Path, dry_run: bool = False) -> Dict[str, Any]:
    started_at = now_iso()
    run_label = manifest.get("run_label") or manifest.get("week_of") or manifest["blog"]["slug"]
    run_id = f"{now_utc().strftime('%Y%m%dT%H%M%SZ')}-{slugify(str(run_label))}"
    output_root = Path(manifest["run"]["output_root"])
    run_dir = output_root / run_id
    ensure_dir(run_dir)

    state: Dict[str, Any] = {
        "run_id": run_id,
        "started_at": started_at,
        "manifest_path": str(manifest_path),
        "dry_run": dry_run,
        "steps": [],
        "status": "running",
        "auth": session_snapshot(),
        "blog": {},
    }

    def mark_step(name: str, status: str, **extra: Any) -> None:
        state["steps"].append({"name": name, "status": status, "timestamp": now_iso(), **extra})
        write_json(run_dir / "run_state.json", state)

    write_json(run_dir / "manifest.resolved.json", manifest)
    write_json(run_dir / "run_state.json", state)

    post: Dict[str, Any] = {"id": manifest["blog"].get("id"), "slug": manifest["blog"].get("slug")}
    public_post: Optional[Dict[str, Any]] = None
    email_package: Optional[Dict[str, Any]] = None
    live_url = manifest["blog"].get("live_url") or ""

    try:
        mark_step("load_manifest", "ok", run_dir=str(run_dir))

        if any(
            manifest["run"].get(key)
            for key in ("create_or_update", "publish", "update_blog_email_fields", "send_test")
        ):
            state["auth"] = ensure_auth_ready(run_dir)
            write_json(run_dir / "run_state.json", state)
            mark_step("auth_preflight", "ok", auth=state["auth"])

        if manifest["run"].get("create_or_update") and not dry_run:
            post = create_or_update_blog(manifest, run_dir)
            state["blog"].update({k: post.get(k) for k in ("id", "slug", "title", "published_at")})
            mark_step("create_or_update_blog", "ok", blog_id=post.get("id"), slug=post.get("slug"))
        else:
            mark_step("create_or_update_blog", "skipped", reason="dry-run or disabled")

        if manifest["run"].get("publish") and not dry_run:
            post = publish_blog(post, run_dir)
            mark_step("publish_blog", "ok", blog_id=post.get("id"), slug=post.get("slug"))
        else:
            mark_step("publish_blog", "skipped", reason="dry-run or disabled")

        live_url = resolve_live_url(post, manifest)
        state["blog"]["live_url"] = live_url
        mark_step("resolve_live_url", "ok", live_url=live_url)

        public_post = maybe_fetch_public_post(post, run_dir)
        if public_post:
            state["public_blog"] = {k: public_post.get(k) for k in ("id", "slug", "title", "published_at")}
            write_json(run_dir / "run_state.json", state)
            mark_step("public_blog_lookup", "ok", slug=public_post.get("slug"))
        else:
            mark_step("public_blog_lookup", "skipped", reason="public lookup unavailable")

        if manifest["run"].get("generate_email_package"):
            email_package = write_email_package(manifest, run_dir, post, live_url)
            state["email_package"] = email_package
            mark_step("generate_email_package", "ok", subject=email_package.get("subject"))
        else:
            mark_step("generate_email_package", "skipped", reason="disabled")

        if manifest["run"].get("update_blog_email_fields") and email_package and not dry_run:
            post = update_blog_email_fields(manifest, post, run_dir, email_package)
            mark_step("update_blog_email_fields", "ok", blog_id=post.get("id"))
        else:
            mark_step("update_blog_email_fields", "skipped", reason="dry-run, disabled, or no email package")

        if manifest["run"].get("send_test") and email_package and not dry_run:
            send_result = send_test_email(manifest, post, run_dir, email_package)
            state["test_send"] = send_result
            mark_step("send_test", "ok")
        else:
            mark_step("send_test", "skipped", reason="dry-run, disabled, or no email package")

        state["status"] = "ok"
        state["finished_at"] = now_iso()
        write_json(run_dir / "run_state.json", state)
        append_jsonl(DEFAULT_LOG_PATH, {
            "run_id": run_id,
            "status": state["status"],
            "started_at": started_at,
            "finished_at": state["finished_at"],
            "manifest_path": str(manifest_path),
            "blog_id": post.get("id"),
            "blog_slug": post.get("slug"),
            "live_url": live_url,
            "dry_run": dry_run,
        })
        return state
    except WeeklyRunError as exc:
        state["status"] = "blocked"
        state["finished_at"] = now_iso()
        state["blocker"] = str(exc)
        write_json(run_dir / "run_state.json", state)
        append_jsonl(DEFAULT_LOG_PATH, {
            "run_id": run_id,
            "status": state["status"],
            "started_at": started_at,
            "finished_at": state["finished_at"],
            "manifest_path": str(manifest_path),
            "blocker": str(exc),
            "dry_run": dry_run,
        })
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the HomeInsight weekly blog + email workflow")
    parser.add_argument("manifest", help="Path to weekly input manifest JSON")
    parser.add_argument("--dry-run", action="store_true", help="Do not call create/update/publish/send-test")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    try:
        manifest = load_manifest(manifest_path)
    except WeeklyRunError as exc:
        ts = now_iso()
        append_jsonl(DEFAULT_LOG_PATH, {
            "run_id": f"{now_utc().strftime('%Y%m%dT%H%M%SZ')}-{slugify(manifest_path.stem)}",
            "status": "blocked",
            "started_at": ts,
            "finished_at": ts,
            "manifest_path": str(manifest_path),
            "blocker": str(exc),
            "stage": "load_manifest",
            "dry_run": args.dry_run,
        })
        print(json.dumps({"status": "blocked", "message": str(exc)}))
        return 1

    try:
        state = execute_run(manifest, manifest_path, dry_run=args.dry_run)
    except WeeklyRunError as exc:
        print(json.dumps({"status": "blocked", "message": str(exc)}))
        return 1

    print(json.dumps({
        "status": state["status"],
        "run_id": state["run_id"],
        "live_url": state.get("blog", {}).get("live_url"),
        "run_state": str(Path(manifest["run"]["output_root"]) / state["run_id"] / "run_state.json"),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
