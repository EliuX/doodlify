# 📊 Doodlify Project Summary

## Overview
Doodlify is a Python CLI tool that automatically adapts frontend projects for special events using AI agents. It analyzes codebases, transforms images, adapts text content, and creates pull requests with event-themed customizations.

## Project Structure

```
doodlify/
├── doodlify/                      # Main package
│   ├── __init__.py                # Package initialization
│   ├── cli.py                     # CLI interface with all commands
│   ├── models.py                  # Pydantic data models
│   ├── config_manager.py          # Configuration and lock file management
│   ├── orchestrator.py            # Main workflow orchestrator
│   ├── git_agent.py               # Local Git operations
│   ├── github_client.py           # GitHub MCP client for remote operations
│   └── agents/                    # AI agents
│       ├── __init__.py
│       ├── analyzer_agent.py      # Codebase analysis using OpenAI
│       ├── image_agent.py         # Image transformation using OpenAI
│       └── text_agent.py          # Text/i18n adaptation using GPT-4
├── .github/
│   └── workflows/
│       └── doodlify.yml           # GitHub Actions workflow (disabled)
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore patterns
├── config.example.json            # Configuration template
├── requirements.txt               # Python dependencies
├── setup.py                       # Package setup
├── README.md                      # Comprehensive documentation
├── QUICKSTART.md                  # Quick start guide
└── PROJECT_SUMMARY.md             # This file
```

## Core Components

### 1. CLI Interface (`cli.py`)
Commands:
- `analyze` - Validate configuration and analyze codebase
- `process` - Process active events
- `push` - Push changes and create PRs
- `clear` - Clear lock data
- `run` - Execute complete workflow
- `status` - Show event status

### 2. Configuration Management (`config_manager.py`)
- Loads and validates `config.json`
- Manages `config-lock.json` state tracking
- Tracks event progress and analysis results
- Prevents duplicate processing

### 3. Data Models (`models.py`)
Pydantic models:
- `ProjectConfig` - Project metadata
- `EventConfig` - Event configuration
- `EventLock` - Event state tracking
- `AnalysisResult` - Codebase analysis results
- `EventProgress` - Processing progress tracking

### 4. Orchestrator (`orchestrator.py`)
Main workflow coordinator:
- Manages all three phases (analyze, process, push)
- Coordinates agents
- Handles Git operations
- Generates commit messages and PR descriptions

### 5. Git Agent (`git_agent.py`)
Local repository operations:
- Clone/update repositories
- Create and manage branches
- Commit changes
- File operations with backups

### 6. GitHub Client (`github_client.py`)
Remote operations using MCP:
- Branch creation
- File pushing
- Pull request creation
- Repository access

### 7. AI Agents

#### Analyzer Agent (`analyzer_agent.py`)
- Identifies frontend framework
- Finds image and text files
- Extracts CSS selectors
- Provides intelligent recommendations

#### Image Agent (`image_agent.py`)
- Transforms images using OpenAI's image editing API
- Generates event-themed variations
- Maintains original composition
- Supports PNG, JPG, JPEG, WebP

#### Text Agent (`text_agent.py`)
- Adapts i18n/localization files
- Uses GPT-4 for contextual text modification
- Maintains tone and language
- Supports nested JSON structures

## Workflow

### Phase 1: Analyze
1. Validate configuration and environment
2. Clone/update target repository
3. Perform AI-powered codebase analysis
4. Cache results in `config-lock.json`
5. Identify active events

### Phase 2: Process
1. Get unprocessed active events
2. For each event:
   - Create event-specific branch
   - Transform images
   - Adapt text files
   - Create backups
   - Commit changes

### Phase 3: Push
1. Push branches to GitHub
2. Create pull requests
3. Update lock file with PR URLs

## Configuration Schema

### config.json
```json
{
  "project": {
    "name": "Project name",
    "description": "Context for AI agents",
    "sources": ["src/", "public/"],
    "targetBranch": "main"
  },
  "defaults": {
    "selector": "CSS selector for elements",
    "branchPrefix": "event/"
  },
  "events": [
    {
      "id": "event-slug",
      "name": "Event Name",
      "description": "Event context for AI",
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD",
      "branch": "branch-name"
    }
  ]
}
```

### config-lock.json (auto-generated)
Tracks:
- Processing status per event
- Analysis results (cached)
- Branch/commit information
- PR URLs
- Modified files
- Errors and timestamps

## Dependencies

### Core
- `python-dotenv` - Environment variable management
- `pydantic` - Data validation
- `click` - CLI framework
- `openai` - AI transformations
- `GitPython` - Git operations
- `mcp` - GitHub MCP protocol

### Optional
- Docker (for GitHub MCP server)
- Node.js/npx (alternative to Docker)

## Environment Variables

Required:
- `GITHUB_PERSONAL_ACCESS_TOKEN` - GitHub access
- `GITHUB_REPO_NAME` - Target repository
- `OPENAI_API_KEY` - OpenAI API access

Optional:
- `GIT_BRANCH_CHANGES_TARGET` - PR target branch

## Features

✅ AI-powered codebase analysis
✅ Image transformation with OpenAI
✅ Text/i18n adaptation with GPT-4
✅ Automatic backup creation
✅ Git branch management
✅ Pull request automation
✅ State tracking to prevent duplicates
✅ GitHub Actions integration
✅ Multiple event support
✅ Configurable CSS selectors
✅ Comprehensive error handling
✅ Progress tracking

## CI/CD Integration

GitHub Actions workflow included (disabled by default):
- Runs daily at 9 AM UTC
- Can be triggered manually
- Persists `config-lock.json` to prevent re-processing
- Requires repository secrets setup

## Safety Features

1. **Backups**: Original files saved with `.original` extension
2. **State Tracking**: Prevents duplicate processing
3. **Branch Isolation**: Each event in separate branch
4. **Review Process**: Changes via pull requests
5. **Error Handling**: Comprehensive error catching and reporting

## Extension Points

The architecture supports:
- Additional AI agents (e.g., CSS, video)
- Custom transformation logic
- Different Git hosting services
- Alternative AI providers
- Custom selectors and filters

## Testing

Basic validation:
```bash
# Test installation
doodlify --help

# Validate configuration
doodlify status --config config.example.json

# Test imports
python -c "from doodlify import cli, orchestrator, models"
```

## Known Limitations

1. Requires valid OpenAI API key with credits
2. GitHub token needs appropriate permissions
3. Large repositories may take time to analyze
4. Image editing quality depends on OpenAI API
5. Text adaptation works best with English content

## Future Enhancements

Potential improvements:
- Support for video transformations
- CSS/styling modifications
- Multiple AI provider support
- Dry-run mode
- Rollback functionality
- Advanced scheduling
- Webhook integration
- Analytics and reporting

## Support

- See README.md for detailed documentation
- See QUICKSTART.md for quick start guide
- Check config.example.json for configuration examples
- Review .env.example for environment setup

---

**Version**: 0.1.0
**Status**: Production Ready
**License**: MIT
