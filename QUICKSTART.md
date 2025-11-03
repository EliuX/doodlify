# 🚀 Quick Start Guide

## Installation

1. Install Doodlify:
```bash
pip install -e .
```

2. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Create your configuration:
```bash
cp config.example.json config.json
# Edit config.json to match your project
```

## Basic Commands

### Check Status
```bash
doodlify status
```

### Analyze Your Project
```bash
doodlify analyze
```

### Process Active Events
```bash
doodlify process
```

### Push Changes to GitHub
```bash
doodlify push
```

### Run Complete Workflow
```bash
doodlify run
```

### Clear Lock Data
```bash
# Clear specific event
doodlify clear --event-id halloween-2024

# Clear all events
doodlify clear
```

## Configuration Example

**config.json:**
```json
{
  "project": {
    "name": "My Website",
    "description": "A React-based website with hero images in public/images/",
    "sources": ["src/", "public/"],
    "targetBranch": "main"
  },
  "defaults": {
    "selector": "img.hero, .banner-image",
    "branchPrefix": "event/"
  },
  "events": [
    {
      "id": "halloween-2024",
      "name": "Halloween 2024",
      "description": "Spooky Halloween theme with pumpkins and ghosts",
      "startDate": "2024-10-15",
      "endDate": "2024-11-01",
      "branch": "halloween-2024"
    }
  ]
}
```

**.env:**
```bash
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
GITHUB_REPO_NAME=username/repository
OPENAI_API_KEY=sk-your_openai_key_here
```

## GitHub Actions Setup

1. Add secrets to your GitHub repository:
   - `GITHUB_PERSONAL_ACCESS_TOKEN`
   - `OPENAI_API_KEY`

2. Enable the workflow by removing `if: false` from `.github/workflows/doodlify.yml`

3. The workflow will run daily at 9 AM UTC or can be triggered manually

## Workflow Phases

### 1. Analyze
- Validates configuration
- Clones/updates repository
- Performs AI codebase analysis
- Caches results in config-lock.json

### 2. Process
- Creates event-specific branches
- Transforms images with OpenAI
- Adapts text/i18n files
- Creates backups (.original files)
- Commits changes locally

### 3. Push
- Pushes branches to GitHub
- Creates pull requests
- Updates config-lock.json with PR URLs

## Tips

- Run `doodlify analyze` first to validate your setup
- Check `doodlify status` to see active events
- Review `config-lock.json` to see cached analysis
- Original files are backed up with `.original` extension
- Use `doodlify clear` to reset processing state

## Troubleshooting

- **"No changes to commit"**: Check event dates and selector
- **"Repository not found"**: Verify GITHUB_REPO_NAME format
- **"OpenAI API Error"**: Check API key and quota
- **Import errors**: Run `pip install -e .` again

For more details, see [README.md](README.md)
