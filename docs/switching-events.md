# Switching to Another Event

Use this guide when you want to start a new cycle for a different event.

## Recommended sequence

```bash
# 1) Finish current event
# (optional) commit manual tweaks in the workspace repo if you made any
cd .doodlify-workspace/<your-repo-name>
git add -A && git commit -m "chore: manual fixes before switching"
cd -

# Push PRs for the current event (run from doodlify project root)
doodlify push

# 2) (optional) refresh analysis cache for the project
doodlify analyze

# 3) Process the next event directly (bypasses date filtering)
doodlify process --event-id <next-event-id>

# 4) Push PRs for the new event
doodlify push
```

## Notes

- Event branches are created by the `process` command automatically using `<branchPrefix><event.branch>`.
- Uncommitted changes inside the workspace repo may be auto-stashed during `process`. Best practice is to commit or discard them before switching events.
