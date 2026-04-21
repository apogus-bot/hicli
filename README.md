# HomeInsight CLI

Public product repo for the **HomeInsight agent-facing CLI**.

This CLI is for real estate agents and teams to manage listings, photos, documents, packages, offers, analysis, and team workflows on HomeInsight.

## Included

- `bin/hi-homeinsight` — main CLI
- `bin/hi-homeinsight-dev` — compatibility shim

## Public CLI scope

This repo intentionally includes only **agent-facing product workflows**.

Included:
- auth + session management
- profile + dashboard
- listings / properties lifecycle
- AI photo staging + editing
- documents + package sharing
- offers
- HomeInsight analysis
- companies / team listings

Intentionally excluded from the public repo:
- admin/internal ops
- sync/cron/webhook tooling
- raw authenticated API escape hatches
- marketing/email campaign commands

## Keep local only

Never commit:

- `~/.config/hi-cli-homeinsight/session.json`
- `~/.config/hi-cli-homeinsight/cookies.txt`
- `~/.config/hi-cli-homeinsight/auth.env`
- `logs/`

The CLI locks `~/.config/hi-cli-homeinsight/` to `0700` and session/cookie files to `0600`, but those files still contain live auth material and must remain local-only.

## Quick start

```bash
chmod +x bin/hi-homeinsight
ln -sf "$PWD/bin/hi-homeinsight" "$HOME/bin/hi-homeinsight"
```

## Auth

```bash
mkdir -p ~/.config/hi-cli-homeinsight
chmod 700 ~/.config/hi-cli-homeinsight
bin/hi-homeinsight auth status
bin/hi-homeinsight auth ensure
```

Create `~/.config/hi-cli-homeinsight/auth.env` locally if you want the CLI to load default auth values from disk.

Passwords are not accepted via `--password` to avoid leaking credentials through shell history or process lists. Put `HI_PASSWORD` in the local auth env file or export it only in a trusted local shell session.

## Core command groups

```bash
hi-homeinsight profile get
hi-homeinsight dashboard summary
hi-homeinsight properties list --limit 20
hi-homeinsight properties get <property_id>
hi-homeinsight photos stage --file living-room.jpg --style modern_minimalist
hi-homeinsight documents list --property <property_id>
hi-homeinsight packages list
hi-homeinsight offers list <property_id>
hi-homeinsight analysis pending
hi-homeinsight companies me
hi-homeinsight team list
```

## JSON input pattern

Most write commands accept any of these:

```bash
hi-homeinsight properties create --json '{"address":"123 Main St","city":"San Jose","state":"CA"}'
hi-homeinsight properties update <id> --file payload.json
cat payload.json | hi-homeinsight offers submit <property_id>
```

## Config overrides

- `HI_APP`
- `HI_SUPABASE`
- `HI_ANON_KEY`
- `HI_REF`
- `HI_CONFIG_DIR`
- `HI_AUTH_ENV_FILE`
- `HI_CLI_BIN`
