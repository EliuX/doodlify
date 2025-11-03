🎨 Doodlify
===============

Automated Event-Based Frontend Customization Tool - Transform your website for special events using AI.

Doodlify is a Python CLI tool that automatically adapts frontend projects for special events like Halloween, Christmas, or custom celebrations. It uses AI agents to intelligently modify images, text, and other visual elements to match your event's theme.

## ✨ Features

- 🤖 **AI-Powered Transformations**: Uses OpenAI's GPT and image editing models to intelligently adapt content
- 🎯 **Smart Analysis**: Automatically identifies files and elements to customize using AI-powered code analysis
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
3. Optionally set `GIT_BRANCH_CHANGES_TARGET` variable

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

Made with ❤️ by the Doodlify team
