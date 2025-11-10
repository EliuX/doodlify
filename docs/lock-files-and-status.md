# Lock Files and Status

Doodlify tracks processing state in a lock file. Understanding where that file lives helps `status` and other commands reflect the correct state.

## Where is the lock file?

- When you run `process`/`analyze`, Doodlify operates inside the cloned workspace repository under:
  - `.doodlify-workspace/<repo-name>/`
- The lock filename is derived from your config file:
  - `config.json` → `config-lock.json`
  - `event.manifest.json` → `event.manifest-lock.json`
- Combined path example:
  - `.doodlify-workspace/<repo-name>/config-lock.json`

## Ensuring `status` reads the correct lock

- Run `doodlify status` from your doodlify project root (where `config.json` lives).
- The CLI aligns to the workspace lock automatically, using `GITHUB_REPO_NAME` to locate `.doodlify-workspace/<repo-name>/<derived-lock-name>`.

## Troubleshooting stale status

- If `status` shows everything as `pending` after a successful `process`:
  - Verify you are running from the doodlify project root.
  - Ensure `.env` contains `GITHUB_REPO_NAME=<owner>/<repo>`.
  - Check for a stale root-level `config-lock.json` (optional to remove it). The authoritative lock is the one under `.doodlify-workspace/<repo-name>/`.
