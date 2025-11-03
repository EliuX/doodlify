Doodlify 🎨
===============

[![CD](https://github.com/EliuX/doodlify/actions/workflows/doodlify.yml/badge.svg)](https://github.com/EliuX/doodlify/actions/workflows/doodlify.yml)
[![Release](https://img.shields.io/github/v/release/EliuX/doodlify?display_name=release)](https://github.com/EliuX/doodlify/releases/latest)
[![License](https://img.shields.io/github/license/EliuX/doodlify)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%20|%203.9%20|%203.10%20|%203.11-blue)](#)

Automated Event-Based Frontend Customization Tool - Transform your website for special events using AI.

Doodlify is a Python CLI tool that automatically adapts frontend projects for special events like Halloween, Christmas, or custom celebrations. It uses AI agents to intelligently modify images, text, and other visual elements to match your event's theme.

## ✨ Features

- 🤖 **AI-Powered Transformations**: Uses OpenAI's GPT and image editing models to intelligently adapt content
- 🎯 **Smart Analysis**: Automatically identifies files and elements to customize using AI-powered code analysis
- 🧠 **Improvement Suggestions**: During analyze, detects repo improvements that boost event quality and auto-creates GitHub issues (deduplicated)
- 🌳 **Git Integration**: Creates separate branches for each event with proper version control
- 🔄 **GitHub Actions Ready**: Easily automate with CI/CD pipelines
- 📝 **i18n Support**: Adapts internationalization files to match event themes
- 🖼️ **Image Transformation**: Automatically generates event-themed variations of images
- 🔒 **Safe Backups**: Creates backup copies of original files before modifications
- 📊 **State Tracking**: Maintains processing state to avoid duplicate work

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Git
- GitHub Personal Access Token
- OpenAI API Key
- Docker (optional, for GitHub MCP server)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/doodlify.git
cd doodlify
```

2. Install dependencies:
```bash
pip install -e .
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your credentials
```

4. Create your configuration:
```bash
cp config.example.json config.json
# Edit config.json to match your project
```

### Basic Usage

```bash
# Analyze your project
doodlify analyze

# Process active events
doodlify process

# Push changes and create PRs
doodlify push

# Or run all phases at once
doodlify run

# Check status
doodlify status

# Clear lock data
doodlify clear --event-id halloween-2024
```

## 📋 Configuration

### Environment Variables (`.env`)

```bash
# Required
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
GITHUB_REPO_NAME=username/repository-name
OPENAI_API_KEY=sk-your_openai_key_here

# Optional
GIT_BRANCH_CHANGES_TARGET=main  # Target branch for PRs
```

### Project Configuration (`config.json`)

```json
{
  "project": {
    "name": "My Project",
    "description": "Description for AI agents",
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
      "description": "Spooky Halloween theme with pumpkins and autumn colors",
      "startDate": "2024-10-15",
      "endDate": "2024-11-01",
      "branch": "halloween-2024"
    }
  ]
}
```

### Configuration Schema

#### `project`
- **name**: Project name
- **description**: Context for AI agents about your project structure
- **sources**: Array of paths to analyze (leave empty for entire repo)
- **targetBranch**: Target branch for pull requests (optional)

#### `defaults`
- **selector**: CSS selector to match elements (e.g., `"img.hero, main > img"`)
- **branchPrefix**: Prefix for event branches (e.g., `"event/"` → `"event/halloween-2024"`)

#### `events[]`
- **id**: Unique identifier (used for branch names)
- **name**: Display name
- **description**: Event context for AI agents
- **startDate/endDate**: Date range (YYYY-MM-DD format)
- **branch**: Branch name suffix

## 🔄 Workflow

Doodlify operates in three phases:

### 1. Analyze Phase
```bash
doodlify analyze
```
- Validates configuration
- Clones/updates target repository
- Performs AI-powered codebase analysis
- Identifies files of interest for modification
- Caches analysis results
- Creates GitHub issues with improvement suggestions (only once per suggestion; tracked in `config-lock.json`)

#### Improvement suggestions
- Source: Heuristics (missing i18n files, missing image assets, missing selectors) and AI considerations
- Tracking: Stored in `config-lock.json` under `reported_suggestions` with a fingerprint to avoid duplicates
- Permissions: Requires Personal Access Token with `Issues: Read and write`

### 2. Process Phase
```bash
doodlify process
```
- Processes all active unprocessed events
- Creates event-specific branches
- Transforms images using OpenAI
- Adapts text/i18n content
- Creates backup files
- Commits changes locally

### 3. Push Phase
```bash
doodlify push
```
- Pushes branches to GitHub
- Creates pull requests
- Updates lock file with PR URLs

## 🤖 AI Agents

### Analyzer Agent
Uses OpenAI to:
- Identify frontend framework (React, Vue, static HTML, etc.)
- Locate visual elements (images, banners, logos)
- Find i18n/localization files
- Extract CSS selectors
- Provide intelligent recommendations
- Produce improvement suggestions for event readiness (e.g., add i18n files, ensure hero images, add selectors)

### Image Agent
Uses OpenAI's image editing API to:
- Transform images to match event themes
- Maintain original composition
- Apply appropriate color schemes
- Add thematic elements

### Text Agent
Uses GPT-4 to:
- Adapt i18n files for events
- Maintain tone and language
- Keep message clarity
- Preserve technical keys

## 📁 File Structure

```
doodlify/
├── doodlify/
│   ├── __init__.py
│   ├── cli.py                 # CLI interface
│   ├── models.py              # Data models
│   ├── config_manager.py      # Configuration handling
│   ├── orchestrator.py        # Main workflow orchestrator
│   ├── git_agent.py          # Local git operations
│   ├── github_client.py       # GitHub MCP client
│   └── agents/
│       ├── analyzer_agent.py  # Codebase analysis
│       ├── image_agent.py     # Image transformations
│       └── text_agent.py      # Text adaptations
├── .github/
│   └── workflows/
│       └── doodlify.yml       # GitHub Actions workflow
├── config.json                # Your configuration
├── event.manifest.json        # Optional: repo-level overrides (lives in target repo)
├── config-lock.json          # State tracking (auto-generated)
├── .env                       # Environment variables
├── requirements.txt
├── setup.py
└── README.md
```

## 🔧 CI/CD Integration

### GitHub Actions

The included workflow file (`.github/workflows/doodlify.yml`) is disabled by default.

To enable:
1. Remove the `if: false` line from the workflow
2. Add secrets to your repository:
   - `GITHUB_PERSONAL_ACCESS_TOKEN`
   - `OPENAI_API_KEY`
3. Ensure the token has repository permissions: `Contents: Read/Write`, `Pull requests: Read/Write` and `Issues: Read/Write`

The workflow:
- Runs daily at 9 AM UTC
- Can be triggered manually
- Commits `config-lock.json` to track state
- Prevents duplicate processing

## 📦 Distributing and Consuming Doodlify

This repository ships build artifacts so client/target projects can adopt the tool without copying code.

Artifacts (when a tag `vX.Y.Z` is pushed):
- GitHub Release: `dist/*.whl` and `dist/*.tar.gz`
- GHCR Docker image: `ghcr.io/<org>/doodlify:latest` and `ghcr.io/<org>/doodlify:vX.Y.Z`
- Optional PyPI publish if credentials are configured

### Client CI: Install from PyPI (preferred if published)
```yaml
jobs:
  doodlify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          python -m pip install --upgrade pip
          pip install doodlify
      - run: |
          doodlify analyze --config event.manifest.json
          doodlify process --config event.manifest.json
          doodlify push --config event.manifest.json
        env:
          GITHUB_PERSONAL_ACCESS_TOKEN: ${{ secrets.GITHUB_PERSONAL_ACCESS_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GITHUB_REPO_NAME: ${{ github.repository }}
```

### Client CI: Install from GitHub Release
```yaml
    - name: Download wheel from latest release
      uses: robinraju/release-downloader@v1.10
      with:
        repository: <org>/<repo>
        latest: true
        fileName: "*.whl"
    - name: Install doodlify from wheel
      run: |
        python -m pip install --upgrade pip
        pip install ./*.whl
```

### Client CI: Run via Docker (GHCR)
```yaml
    - name: Run doodlify via Docker
      run: |
        docker run --rm \
          -e GITHUB_PERSONAL_ACCESS_TOKEN=${{ secrets.GITHUB_PERSONAL_ACCESS_TOKEN }} \
          -e OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }} \
          -e GITHUB_REPO_NAME=${{ github.repository }} \
          -v ${{ github.workspace }}:/work \
          -w /work \
          ghcr.io/<org>/doodlify:latest \
          doodlify run --config event.manifest.json
```

Notes:
- Client repos should own `event.manifest.json` at the repo root. The tool reads it after clone to override `project/defaults/events`.
- Lock files are written under `.doodlify-workspace/<repo>/` and should not be committed. Upload as artifacts if needed.

## 📊 State Management

Doodlify uses `config-lock.json` to track:
- Processing status of each event
- Analysis results (cached)
- Branch and PR information
- Modified files
- Commit SHAs
- Errors and timestamps
- Reported improvement suggestions (title, fingerprint, issue number)

Lock filename note:
- The lock file name is derived from the config file name you pass to the CLI.
- Examples:
  - `--config config.json` → `config-lock.json`
  - `--config event.manifest.json` → `event.manifest-lock.json`

This prevents duplicate work in CI/CD environments.

## 🛠️ Advanced Usage

### Custom Selectors

Target specific elements:
```json
{
  "defaults": {
    "selector": "img.hero, main > img, [data-theme-image]"
  }
}
```

### Event-Specific Analysis

Each event can have dedicated analysis results:
```bash
doodlify analyze
# Analysis is cached in config-lock.json
```

### Clear and Reprocess

```bash
# Clear specific event
doodlify clear --event-id halloween-2024

# Clear all
doodlify clear
```

## 🧩 Optional Repo Manifest (event.manifest.json)

You can place an `event.manifest.json` file in the target repository (at the repo root) to override parts of your configuration after cloning. This is useful when the target repo wants to customize selectors, defaults, or events without editing the automation project.

Precedence (highest last):
- `config.json` (passed to the CLI)
- `event.manifest.json` (in the target repo) overrides `project`, `defaults`, and `events`

Example `event.manifest.json` in the target repo:
```json
{
  "defaults": {
    "selector": "img.hero, [data-event-adaptable]",
    "branchPrefix": "feature/event/"
  },
  "project": {
    "targetBranch": "main"
  }
}
```

Notes:
- Manifest is optional. If present, it is applied after cloning and before analysis.
- Only the top-level keys `project`, `defaults`, and `events` are considered.
- The manifest is intended as a consumer-owned override; your automation repo still keeps a boilerplate `config.example.json`.

## 🐛 Troubleshooting

### "No changes to commit"
- Check if event dates are active
- Verify selector matches elements in your code
- Ensure images are in supported formats (PNG, JPG, WebP)

### "Repository not found"
- Verify `GITHUB_REPO_NAME` format: `owner/repo`
- Check GitHub token has repo access

### "OpenAI API Error"
- Verify API key is valid
- Check API quota/billing
- Ensure image format is supported

### MCP Server Issues
If Docker is unavailable, install Node.js and the tool will use npx:
```bash
npm install -g @modelcontextprotocol/server-github
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- OpenAI for GPT and image editing APIs
- GitHub MCP for repository operations
- The open-source community for the amazing tools and libraries

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the troubleshooting section

---

Made with ❤️ by the [EliuX][mailto: eliecerhdz@gmail.com]
