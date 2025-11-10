# Reprocessing Specific Files

Use this guide when you want to re-run processing for particular files without clearing everything.

## Option 1: Restore then process (safe)

Restores the original bytes from the `.original` backup and removes the backup, making the file eligible for a normal run.

```bash
# Restore from backup and clear processed state for those files
doodlify restore \
  --event-id <event-id> \
  --files path/to/file1.png,path/to/file2.png

# Re-run processing just for those files
doodlify process \
  --event-id <event-id> \
  --only path/to/file1.png,path/to/file2.png
```

## Option 2: Force reprocess (override backups)

Skips the backup check and re-transforms in-place. Backups remain on disk.

```bash
doodlify process \
  --event-id <event-id> \
  --only path/to/file1.png \
  --force
```

## Notes

- Backups: The first time a file is transformed, a sibling `.original` copy is created.
- Default behavior: Files with an existing `.original` are skipped to avoid duplicate work.
- Use `restore` to reset a file to its pre-processed bytes and remove the backup.
