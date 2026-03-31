# Model Context Protocol (MCP) Fast-Learning Guide

The **Model Context Protocol (MCP)** is an open standard that acts like a **"USB-C port for AI."** It allows Large Language Models (LLMs) to securely connect to your local data, tools, and APIs without needing custom code for every different AI application.

---

## 1. The Big Picture: Architecture
MCP follows a **Host-Client-Server** model. Understanding this is key to how they work.

*   **MCP Host:** The AI application you are using (e.g., Claude Desktop, VS Code, Cursor). It contains the LLM.
*   **MCP Client:** A small piece of code inside the Host that manages connections.
*   **MCP Server:** **This is what you build.** It is a standalone program that exposes specific data or functions to the AI.

**How they talk:** They use **JSON-RPC 2.0**. You don’t need to worry about the math; the SDKs handle it.

---

## 2. Core Building Blocks (Primitives)
Every MCP server is built using three main components:

| Component | What it is | Example Use Case |
| :--- | :--- | :--- |
| **Tools** | **Executable functions** the AI can call. | "Search my database," "Send an email," "Resize this image." |
| **Resources** | **Read-only data** the AI can pull in. | "Read `config.json`," "Get the current weather log," "Fetch git logs." |
| **Prompts** | **Templates** to guide the AI's behavior. | "Act as a code reviewer," "Summarize these meeting notes." |

---

## 3. Communication Channels (Transports)
MCP servers can connect to the Host in two primary ways:

1.  **Stdio (Standard Input/Output):** Most common for **local** development. The host starts your server as a child process and communicates via text streams. Highly secure because it doesn't open network ports.
2.  **HTTP with SSE (Server-Sent Events):** Used for **remote** servers. The server runs as a web service and "streams" data back to the client.

---

## 4. How to Build Your First Server (Quickest Start)
The fastest way to build is using the **Python FastMCP** framework or the **TypeScript SDK**.

### Python Example (FastMCP)
FastMCP is a high-level wrapper that makes building servers incredibly easy.

**1. Install the library:**
```bash
pip install fastmcp
```

**2. Create `server.py`:**
```python
from fastmcp import FastMCP

# 1. Initialize the server
mcp = FastMCP("MyFirstServer")

# 2. Add a Tool (Function the AI can run)
@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Adds two numbers together."""
    return a + b

# 3. Add a Resource (Data the AI can read)
@mcp.resource("config://app-settings")
def get_config() -> str:
    """Provides application configuration context."""
    return "Theme: Dark, Language: English, Version: 1.0"

if __name__ == "__main__":
    mcp.run()
```

---

## 5. Typical Project Structure
When building a production-ready MCP server, your project usually looks like this:

```text
my-mcp-server/
├── server.py (or index.ts)  <-- Entry point where you define tools
├── pyproject.toml           <-- Dependencies (if Python)
├── package.json             <-- Dependencies (if TypeScript)
└── README.md                <-- Instructions for the user
```

---

## 6. Connecting the Server to a Host
To use your server in an app like **Claude Desktop**, you must tell the app where your server lives.

1.  Open your `claude_desktop_config.json` file.
2.  Add your server path:
```json
{
  "mcpServers": {
    "my-cool-server": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```
3.  **Restart** the host application. The AI will now "see" your new tools.

---

## 7. Fast Learning Summary
*   **Goal:** Give AI access to things it can't normally see (local files, private APIs).
*   **Building:** Use **Python (FastMCP)** or **TypeScript** SDKs.
*   **Defining:** Use `@tool` for actions and `@resource` for data.
*   **Security:** By default, servers run locally and only share what you explicitly define.
*   **Discovery:** The Host automatically asks the Server "What can you do?" during the connection handshake.

