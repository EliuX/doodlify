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
- **reportSuggestions**: Boolean map controlling which suggestions are auto-filed as GitHub issues. Use keys below. Default enables core items and disables optional ones.

Example:
```json
{
  "defaults": {
    "reportSuggestions": {
      "i18n": false,
      "css_variables": true,
      "data_attrs": true,
      "svg_usage": true,
      "global_css": true,
      "marker_styles": true,
      "favicon_variants": true,
      "favicon_establish": true,
      "og_variants": true,
      "og_add": true,
      "selectors_guidance": true,
      "ai_considerations": true
    }
  }
}
```

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

##### Suggestion keys and defaults

The analyzer attaches a stable `key` to each suggestion. The orchestrator consults `defaults.reportSuggestions[key]` to decide if it should be filed.

- Optional by default (false):
  - `i18n` → "Optional: Centralize user-facing copy in i18n files"

- Core by default (true):
  - `css_variables` → Add CSS variables for theme tokens (colors, spacing)
  - `data_attrs` → Add data attributes to mark adaptable elements
  - `svg_usage` → Prefer SVG for logos/illustrations to enable recoloring
  - `global_css` → Ensure a global stylesheet or theme entrypoint exists
  - `marker_styles` → Style list markers (e.g., vignettes) to allow event variations
  - `favicon_variants` → Provide event-ready favicon/touch icon variants (if favicon assets exist)
  - `favicon_establish` → Establish predictable favicon/touch icon assets (if none exist)
  - `og_variants` → Provide seasonal Open Graph social preview variants (if `og:image` exists)
  - `og_add` → Add Open Graph image meta for social sharing (if `og:image` missing)
  - `selectors_guidance` → Add CSS selectors or data-attributes to mark event-adaptable elements (if no selector in config)
  - `ai_considerations` → Apply analyzer considerations to improve event readiness

You can override any of these in your `config.json` under `defaults.reportSuggestions`.

CLI override:
- Pass `--report-all` to `doodlify analyze` or `doodlify run` to report everything (including those set to false). These will be logged as OPTIONAL when filed due to the flag.

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

Advanced flags:

```bash
# Process a specific event (bypasses active/unprocessed filters)
doodlify process --event-id halloween-2025

# Process only certain files for an event
doodlify process --event-id halloween-2025 \
  --only frontend/web-ui/src/images/hero-ecommerce-construction.png,frontend/web-ui/src/images/hero-telephony.png

# Force reprocess even if `.original` backups exist
doodlify process --event-id halloween-2025 \
  --only frontend/web-ui/src/images/hero-ecommerce-construction.png \
  --force
```

### 3. Push Phase
```bash
doodlify push
```
- Pushes branches to GitHub
- Creates pull requests
- Updates lock file with PR URLs

### Push and PR workflow when you have local tweaks
If you made additional edits inside the workspace repo (e.g., fixed CSS or HTML) after processing, commit them first and then run `doodlify push`:

```bash
# The workspace repository lives here
cd .doodlify-workspace/<your-repo-name>

# Commit your changes on the event branch (created during process)
git status
git add -A
git commit -m "chore: manual fixes before PR"

# Return to your doodlify project root and push/PR
cd -
doodlify push
```

Notes:
- The push step looks at processed events that haven’t been pushed yet and creates PRs automatically.
- The event branch naming is `<branchPrefix><event.branch>` (e.g., `feature/event/halloween-2025`).

### Workflow for another event

Sometimes you’ll want to run a new cycle for a different event (or re-run with different settings).

- Activate or target the event explicitly:
```bash
# Re-run analysis (refreshes cache if needed)
doodlify analyze

# Process a specific event directly (bypasses date-based filtering)
doodlify process --event-id <event-id>

# Then push and open PRs
doodlify push
```

- If you want to reprocess previously modified files for the same event, use either:
  - `doodlify restore --event-id <event-id> --files <comma-separated files>` to restore originals and process again, or
  - `doodlify process --event-id <event-id> --only <files> --force` to reprocess even if backups exist.

- If you need a clean slate for an event (clears its state in the lock file):
```bash
doodlify clear --event-id <event-id>
```

Transition guidance:
- Each event is processed on its own branch. Creating a new event branch is handled by `process`; it also auto-stashes any local, uncommitted changes in the workspace repo to avoid conflicts.
- Best practice:
  - Finish and push the current event’s branch (`doodlify push`).
  - Commit any extra manual tweaks inside `.doodlify-workspace/<repo>` before switching.
  - Run `doodlify analyze` (optional but recommended) and `doodlify process --event-id <next-event>` for the new event.

## 📚 Documentation

For focused, task-oriented guides, see the `docs/` folder:

- [Push and PR workflow](docs/push-and-pr.md)
- [Switching to another event](docs/switching-events.md)
- [Reprocessing specific files](docs/reprocessing-files.md)
- [Lock files and status](docs/lock-files-and-status.md)

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

### Reprocessing a single file

There are two supported workflows to re-run an individual file without clearing everything:

1) Restore from backup, then process (safe, resets the file to its exact original)

```bash
# Restore the current file from its `.original` backup and remove the backup
doodlify restore \
  --event-id halloween-2025 \
  --files frontend/web-ui/src/images/hero-ecommerce-construction.png

# Re-run processing for just that file
doodlify process \
  --event-id halloween-2025 \
  --only frontend/web-ui/src/images/hero-ecommerce-construction.png
```

2) Force process (skip the backup check and re-transform in place)

```bash
doodlify process \
  --event-id halloween-2025 \
  --only frontend/web-ui/src/images/hero-ecommerce-construction.png \
  --force
```

Notes:
- Backups: When a file is first transformed, Doodlify creates a `.original.{ext}` sibling (e.g., `image.original.png`).
- Default skip: Subsequent runs skip files with existing `.original.{ext}` to avoid duplicate work.
- Restore: `doodlify restore` puts the original bytes back into the current file and removes the `.original.{ext}`, making it eligible for normal processing again.
- Force: `--force` tells the processor to ignore `.original.{ext}` and reprocess anyway.

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

Made with ❤️ by [EliuX][mailto: eliecerhdz@gmail.com]
