# Push and PR Workflow

Use this guide when you want to push processed changes and open pull requests.

## Prerequisites

- Run processing first so there are committed changes on the event branch:
  - `doodlify process` or `doodlify process --event-id <event-id>`
- Ensure `.env` has:
  - `GITHUB_PERSONAL_ACCESS_TOKEN`
  - `OPENAI_API_KEY`
  - `GITHUB_REPO_NAME`

## If you made manual tweaks in the workspace repo

The workspace repo lives under `.doodlify-workspace/<your-repo-name>`.

```bash
cd .doodlify-workspace/<your-repo-name>
# Commit your tweaks on the event branch created during process
git status
git add -A
git commit -m "chore: manual fixes before PR"
cd -
```

## Push and create PRs

Run from your doodlify project root (where `config.json` lives):

```bash
doodlify push
```

What happens:

- Pushes any processed-but-not-pushed event branches.
- Creates a PR for each event and stores the PR URL in the lock.

## Notes

- Branch naming: `<branchPrefix><event.branch>` (e.g., `feature/event/halloween-2025`).
- If you run `doodlify push` inside the workspace repo, you may see `--config` errors. Always run from the doodlify project root.
