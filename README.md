# MCP to Claude Skills Converter

This is a Python script that converts MCP (Model Context Protocol) servers into Claude Code Skills packages. It automatically generates skill packages with AI-powered descriptions, wrapper scripts, and documentation.

## Overview

This script reads MCP server configurations from Claude's config files and converts them into standalone Claude Skills that can be used with Claude Code. Each generated skill includes:
- A Python wrapper script for tool execution
- AI-generated skill descriptions
- Complete tool reference documentation
- Usage instructions

## Features

- **Automatic Configuration Detection**: Scans standard Claude config locations across different platforms
- **AI-Powered Descriptions**: Uses OpenAI-compatible APIs to generate skill descriptions
- **Universal Wrapper Generation**: Creates Python scripts that work with any MCP server
- **Cross-Platform Support**: Works on macOS, Windows, and Linux
- **Environment Variable Support**: Loads configuration from `.env` files

## Prerequisites

- Python 3.7+
- `uv` package manager
- MCP Python package
- `python-dotenv` (optional, for .env support)
- OpenAI-compatible API access (for AI descriptions)

## Installation

1. Install required dependencies:
```bash
pip install mcp python-dotenv openai
```

2. Install `uv` if not already installed:
```bash
pip install uv
```

## Configuration

Create a `.env` file in the same directory as `main.py` with the following variables:

```env
# AI Configuration (for generating skill descriptions)
DS_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-chat
```

## Usage

### Basic Usage

Run the script without arguments to auto-detect Claude's configuration:

```bash
python main.py
```

### Specify Configuration File

Provide a specific configuration file path:

```bash
python main.py /path/to/your/config.json
```

## Generated Skill Structure

For each MCP server, the script creates a directory structure like:

```
mcp_skills/
└── server-name/
    ├── SKILL.md              # Main skill documentation with AI description
    ├── reference.md          # Complete tool reference
    └── scripts/
        └── server_name_wrapper.py  # Python wrapper script
```

### Generated Files

1. **SKILL.md**: Contains skill metadata, AI-generated description, and usage instructions
2. **reference.md**: Detailed documentation of all available tools and their schemas
3. **scripts/[server]_wrapper.py**: Python script that interfaces with the MCP server

## Using Generated Skills

To use a generated skill, execute the wrapper script using `uv`:

```bash
uv run --quiet --with mcp /path/to/skill/scripts/server_wrapper.py "tool_name" '{"arg": "value"}'
```

## Configuration File Detection

The script searches for Claude configuration files in the following order:

1. Command-line provided path
2. macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
3. Windows: `%APPDATA%\Claude\claude_desktop_config.json`
4. Linux: `~/.config/Claude/claude_desktop_config.json`
5. Claude Code CLI: `~/.claude.json`

## AI Description Generation

When an API key is provided, the script uses AI to generate skill descriptions that:
- Summarize the skill's capabilities
- Identify primary use cases
- Follow Anthropic's skill description guidelines
- Are optimized for Claude Agent Router compatibility

If AI generation fails, a fallback description is created using the server name and top tools.

## Error Handling

The script includes comprehensive error handling for:
- Missing configuration files
- MCP server connection failures
- AI API errors
- File system permissions
- Invalid JSON configurations

## Output

All generated skills are placed in the `mcp_skills/` directory by default. Each skill is self-contained and can be used independently.

## Example Workflow

1. Place `main.py` in your project directory
2. Create a `.env` file with your AI API key
3. Run `python main.py`
4. Find generated skills in the `mcp_skills/` directory
5. Use skills with the provided `uv` commands

## Troubleshooting

- **No config found**: Ensure Claude is installed and has been configured
- **AI generation fails**: Check your API key and base URL in the `.env` file
- **Wrapper script errors**: Verify the MCP server is properly installed and accessible
- **Permission errors**: Ensure write permissions for the output directory

## Dependencies

- `mcp`: Model Context Protocol client library
- `openai`: OpenAI-compatible API client
- `python-dotenv`: Environment variable loading
- `pathlib`: Path manipulation
- `asyncio`: Asynchronous programming support
