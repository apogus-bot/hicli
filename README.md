# HomeInsight CLI

Standalone product repo for the HomeInsight command line client and optional weekly runner.

## Included

- `bin/hi-homeinsight` — main CLI
- `bin/hi-homeinsight-dev` — compatibility shim

## Keep local only

Never commit:

- `~/.config/hi-cli-homeinsight/session.json`
- `~/.config/hi-cli-homeinsight/cookies.txt`
- `~/.config/hi-cli-homeinsight/auth.env`
- `weekly/runs/`
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
```

Then:

```bash
bin/hi-homeinsight auth status
bin/hi-homeinsight auth ensure
```

Create `~/.config/hi-cli-homeinsight/auth.env` locally if you want the CLI to load default auth values from disk.

Passwords are no longer accepted via `--password` to avoid leaking credentials through shell history or process lists. Put `HI_PASSWORD` in the local auth env file (or export it only in a trusted local shell session).

## Config overrides

- `HI_APP`
- `HI_SUPABASE`
- `HI_ANON_KEY`
- `HI_REF`
- `HI_CONFIG_DIR`
- `HI_AUTH_ENV_FILE`
- `HI_CLI_BIN`

