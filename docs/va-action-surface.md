# HomeInsight VA Action Surface

Concise command map for the customer-facing HomeInsight assistant CLI.

## Core session

- `auth status` — inspect current login/session state
- `auth ensure` — refresh or re-login and rebuild cookies if needed
- `whoami` — show current authenticated user

## Agent workflow actions

- `dashboard` — fetch the agent dashboard summary
- `properties list [--limit N]` — list available properties
- `properties get <property_id>` — fetch property details
- `properties create` — quick-create a property from JSON on stdin
- `leads` — list the current agent lead set
- `offers list <property_id>` — list offers for a property
- `offers get <property_id> <offer_id>` — inspect one offer
- `offers respond <property_id> <offer_id> <json>` — accept/reject/counter an offer
- `docs list` — list my documents
- `docs shared` — list documents shared with me
- `docs packages` — list document packages
- `docs upload <property_id>` — upload a property document from stdin
- `docs analytics <property_id> <doc_id>` — inspect document engagement
- `onboarding` — complete onboarding flow

## Marketing / content actions

- `blog list [limit]` — list blog posts
- `blog get <id_or_slug>` — fetch one blog post
- `blog create --title ... --content-file ...` — create a blog post
- `blog update <id> [fields...]` — patch content, SEO, image, and email fields
- `blog publish <id>` — publish a post
- `blog send-test <id> [...]` — send a test email for a post
- `blog send-campaign <id> --audience ... [...]` — send the full campaign
- `weekly/run_weekly.py <manifest> [--dry-run]` — wrapper for the full weekly blog/email workflow

## Expected VA behavior

- Prefer high-level task verbs in UX copy: *check auth, list properties, review offers, publish post, send test email*.
- Keep secrets local in `~/.config/hi-cli-homeinsight/` and never commit session, cookies, or auth env files.
