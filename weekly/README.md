# HomeInsight Weekly Runner

Optional workflow wrapper around `bin/hi-homeinsight`.

## What it does

1. Loads a weekly manifest.
2. Creates or updates a blog post.
3. Publishes the post.
4. Resolves the live URL.
5. Generates an email package.
6. Updates the blog record with email fields.
7. Sends a test email.
8. Writes local run state under `weekly/runs/`.

## Dry run

```bash
weekly/run_weekly.py weekly/examples/weekly-input.example.json --dry-run
```
