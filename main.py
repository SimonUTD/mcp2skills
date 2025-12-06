import asyncio
import json
import os
import sys
import re
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI
from dotenv import load_dotenv

# --- 1. LOAD .ENV & CONFIGURATION ---
try:

    load_dotenv()
    print("ℹ️  Loaded environment variables from .env")
except ImportError:
    print("⚠️  Warning: 'python-dotenv' not found. Only system env vars will be used.")
    print("   Install it via: pip install python-dotenv")

# AI Configuration
AI_API_KEY = os.getenv("DS_API_KEY")
AI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")

# Output Directory
OUTPUT_DIR = "mcp_skills"

# Standard config paths for Claude
HOME = Path.home()
POSSIBLE_CONFIGS = [
    HOME / "Library/Application Support/Claude/claude_desktop_config.json",  # macOS
    Path(os.environ.get("APPDATA", "")) / "Claude/claude_desktop_config.json", # Windows
    HOME / ".config/Claude/claude_desktop_config.json",                      # Linux
    HOME / ".claude.json",                                                   # Claude Code CLI
]
# ------------------------------------

def to_snake_case(name):
    """Converts 'My Server-Name' to 'my_server_name'."""
    s = re.sub(r'[^a-zA-Z0-9]', '_', name)
    s = re.sub(r'_+', '_', s) 
    return s.lower().strip('_')

def to_kebab_case(name):
    """Converts 'My Server Name' to 'my-server-name'."""
    s = re.sub(r'[^a-zA-Z0-9]', '-', name)
    s = re.sub(r'-+', '-', s)
    return s.lower().strip('-')

def get_ai_description(server_name, tools):
    """
    调用 AI 生成符合 Anthropic 标准的路由描述。
    """
    if not AI_API_KEY:
        print(f"   ⚠️  Skipping AI description: OPENAI_API_KEY not found in .env or env vars.")
        return None

    try:
        client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)

        # 整理工具列表（限制长度以节省 Token）
        tool_list_str = ""
        for t in tools:
            desc = t.description.strip().split('\n')[0] if t.description else "No description"
            tool_list_str += f"- {t.name}: {desc}\n"
        
        # 核心 Prompt
        prompt = f"""
You are an expert in writing clear, concise, and useful “Skill Description” entries for Claude Skills documentation.

**Task:**  
Given an MCP server name and a list of its tools, write a single **Skill Description** that accurately summarizes what the skill does and when to use it, in a format suitable for a Claude Agent Router.

**Input format:**
- MCP Name: [server_name]
- Tools: [list of tool names and optional brief descriptions]

**Output Guidelines:**
1. **Structure** (following these parts in one paragraph or two short sentences):
   - Start with a **capability summary** (what this skill enables).
   - Specify **primary use cases or triggers** (when to use it).
   - Optionally include **key constraints or notable features** if relevant.

2. **Style:**  
   - Be concise, natural, and agent-friendly.
   - Use present tense, active voice.
   - Focus on user goals, not just tool names.
   - Avoid markdown, code blocks, or bullet points in the final description.

3. **Length:**  
   - Aim for 1–2 clear sentences, or a short paragraph (about 30–70 words).

**Examples for reference:**

Example 1:  
“Creating algorithmic art using p5.js with seeded randomness and interactive parameter exploration. Use this when users request creating art using code, generative art, algorithmic art, flow fields, or particle systems. Create original algorithmic art rather than copying existing artists' work to avoid copyright violations.”

Example 2:  
“Presentation creation, editing, and analysis. When Claude needs to work with presentations (.pptx files) for: (1) Creating new presentations, (2) Modifying or editing content, (3) Working with layouts, (4) Adding comments or speaker notes, or any other presentation tasks.”

---

Now, generate the Skill Description for:

**MCP Name:**  
{server_name}

**Tools:**  
{tool_list_str}
"""
        print(f"   🧠 Requesting AI description for '{server_name}'...")
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            stream=False,
            extra_body={"thinking": {"type": "enabled"}}
        )
        
        # 清洗结果，确保 YAML 安全
        raw_content = response.choices[0].message.content.strip()
        cleaned_content = raw_content.replace('"', "'").replace('\n', ' ').strip("'")
        return cleaned_content

    except Exception as e:
        print(f"   ⚠️  AI Generation failed: {e}")
        return None

async def generate_skill_package(name, config):
    """Generates a fully compliant, robust Claude Skill package using uv."""
    
    # 1. Prepare Configuration
    command = config.get("command")
    args = config.get("args", [])
    env = config.get("env", {})
    full_env = os.environ.copy()
    full_env.update(env)

    if not command:
        print(f"⚠️  Skipping '{name}': No command found.")
        return

    print(f"🔌 Connecting to '{name}'...")

    # 2. Connect to MCP Server to fetch real tools
    server_params = StdioServerParameters(command=command, args=args, env=full_env)

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                tools = result.tools
                
                if not tools:
                    print(f"   No tools found for '{name}'. Skipping.")
                    return

                # --- DIRECTORY STRUCTURE ---
                skill_id = to_kebab_case(name)
                script_name = to_snake_case(name) + "_wrapper.py"
                
                skill_root = Path(OUTPUT_DIR) / skill_id
                scripts_dir = skill_root / "scripts"
                scripts_dir.mkdir(parents=True, exist_ok=True)

                # ==========================================
                # FILE 1: scripts/wrapper.py (Generated Code)
                # ==========================================
                py_filename = scripts_dir / script_name
                config_str = json.dumps({"command": command, "args": args, "env": env}, indent=4)
                
                # Wrapper Python Content
                py_content = f"""import asyncio
import json
import os
import sys

# Force UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    sys.stderr.write("Error: 'mcp' module not found.\\n")
    sys.exit(1)

# Configuration
SERVER_CONFIG = {config_str}

async def _run_tool(tool_name, arguments):
    env = os.environ.copy()
    env.update(SERVER_CONFIG.get("env", {{}}))
    
    # Debug info to stderr
    sys.stderr.write(f"[Wrapper] Connecting to server to run '{{tool_name}}'...\\n")

    server_params = StdioServerParameters(
        command=SERVER_CONFIG["command"],
        args=SERVER_CONFIG["args"],
        env=env
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result

def call_tool(tool_name, arguments=None):
    if arguments is None: arguments = {{}}
    try:
        result = asyncio.run(_run_tool(tool_name, arguments))
        
        output = []
        if hasattr(result, 'content') and result.content:
            for item in result.content:
                if item.type == 'text': output.append(item.text)
                elif item.type == 'resource': output.append(f"[Resource: {{item.resource.uri}}]")
                else: output.append(str(item))
        
        final_output = "\\n".join(output)
        if not final_output:
            return "Tool executed successfully. No text content returned."
            
        return final_output
    except Exception as e:
        sys.stderr.write(f"[Wrapper] Exception: {{str(e)}}\\n")
        return f"Error executing {{tool_name}}: {{str(e)}}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: uv run --quiet --with mcp {{os.path.basename(__file__)}} <tool_name> '<json_args>'")
        sys.exit(1)
        
    t_name = sys.argv[1]
    t_args = {{}}
    if len(sys.argv) > 2:
        try:
            t_args = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print(f"Error: Arguments must be valid JSON.")
            sys.exit(1)
            
    print(call_tool(t_name, t_args))
"""
                with open(py_filename, "w", encoding="utf-8") as f:
                    f.write(py_content)

                # ==========================================
                # FILE 2: reference.md
                # ==========================================
                ref_filename = skill_root / "reference.md"
                ref_content = f"# {name} Reference\n\n"
                for tool in tools:
                    ref_content += f"## `{tool.name}`\n{tool.description}\n```json\n{json.dumps(tool.inputSchema, indent=2)}\n```\n\n"
                with open(ref_filename, "w", encoding="utf-8") as f:
                    f.write(ref_content)

                # ==========================================
                # FILE 3: SKILL.md (The Brain - AI Enhanced)
                # ==========================================
                
                # 1. Attempt AI Generation
                description = get_ai_description(name, tools)
                
                # 2. Fallback if AI fails or Key is missing
                if not description:
                    top_tools = [t.name for t in tools[:4]]
                    description = f"Integration with {name}. Capabilities: {', '.join(top_tools)}."
                    # Make safe for YAML
                    description = description.replace('"', "'").replace('\n', ' ')

                md_filename = skill_root / "SKILL.md"
                
                md_content = f"""---
name: {skill_id}
description: "{description}"
---

# {name} Skill

This skill allows you to run tools from **{name}**.

## Available Tools
"""
                for tool in tools:
                    # Clean description for list view
                    short_desc = tool.description.split('.')[0] if tool.description else 'Run tool'
                    md_content += f"- `{tool.name}`: {short_desc}\n"

                md_content += f"""
## usage
To use a tool, you must execute the Python wrapper script directly using `uv`.
This ensures dependencies (like `mcp`) are installed automatically.

### Step 1: Locate the Script
First, find the absolute path to the `scripts/{script_name}` file in this skill's directory.

### Step 2: Execute via CLI
Run the following command in your terminal. 
**Note:** Use `--quiet` to suppress installation logs.

```bash
uv run --quiet --with mcp /absolute/path/to/{skill_id}/scripts/{script_name} "tool_name" '{{"arg_name": "value"}}'
```

"""
            with open(md_filename, "w", encoding="utf-8") as f:
                f.write(md_content)

            print(f"   ✅ Created '{skill_id}'")

    except Exception as e:
        print(f"❌ Error processing '{name}': {e}")


async def main():
    print("--- MCP to Claude Code Skills (UV Mode + .env Support) ---")

    # 1. Locate Config
    config_path = None
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        config_path = Path(sys.argv[1])
    else:
        for path in POSSIBLE_CONFIGS:
            if path.exists():
                config_path = path
                break

    if not config_path:
        print("❌ No config file found. Usage: python mcp_batch_convert.py /path/to/config.json")
        return

    print(f"📂 Reading config: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    servers = data.get("mcpServers", {})
    if not servers:
        print("⚠️  No 'mcpServers' found.")
        return

    # 2. Convert
    for name, config in servers.items():
        if config.get("type", "stdio") == "stdio":
            await generate_skill_package(name, config)

    print(f"\n🎉 Done! Skills generated in '{OUTPUT_DIR}/'.")


if __name__ == "__main__":
    asyncio.run(main())
