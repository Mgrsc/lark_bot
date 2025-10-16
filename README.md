# 🤖 Lark AI Bot

An AI assistant for Lark (Feishu) that supports customizable personalities, conversation context, and tool integration via Model Context Protocol (MCP).

## ✨ Features

- 🎯 **LLM Integration** - Compatible with OpenAI and other OpenAI-compatible APIs
- 🔧 **MCP Support** - Connect external tools through Model Context Protocol
- 🎭 **Customizable Roles** - Define bot personalities via text files
- 💾 **Conversation Memory** - Redis-based context retention
- 🔄 **Smart Tool Refresh** - Automatic MCP tool list updates
- 📱 **Smart Response** - Responds to @mentions in groups, all messages in DM

## 🚀 Quick Start

### Prerequisites

- Lark (Feishu) application credentials
- Redis/Upstash instance
- LLM API key (OpenAI or compatible service)

### Environment Setup

```bash
cp .env.example .env
# Edit .env with your credentials
```

**Required Variables:**
```bash
# Lark App
LARK_APP_ID=your_app_id
LARK_APP_SECRET=your_app_secret
LARK_VERIFICATION_TOKEN=your_token

# LLM Service
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4-turbo

# Redis
REDIS_URL=redis://localhost:6379/0
```

**Optional Variables:**
```bash
# Model Parameters (not set by default, only sent if explicitly configured)
# Uncomment and set these ONLY if you need to customize LLM behavior
# If not set, these parameters won't be sent to the LLM API
# LLM_TEMPERATURE=0.7
# LLM_TOP_P=1.0
# LLM_MAX_TOKENS=4096

# MCP Servers (optional)
# MCP_SERVER_1_URL=http://localhost:8000/mcp
# MCP_SERVER_1_TOKEN=optional_token
```

See [.env.example](.env.example) for full documentation.

---

## 📦 Deployment

### Option 1: Local Development

**Requirements:** Python 3.11+, Redis

```bash
# Install dependencies
uv sync

# Run the application
uv run flask run
```

The app will be available at `http://localhost:5000`.

### Option 2: Docker

**Requirements:** Docker, Docker Compose

```bash
# Build and run
docker-compose up --build
```

The app will be available at `http://localhost:5001`.

**Production deployment:**
```bash
docker build -t lark-bot .
docker run -d \
  --env-file .env \
  -p 8000:8000 \
  lark-bot
```

### Option 3: Vercel (Serverless)

**Requirements:** Vercel account

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel deploy
```

**Configure environment variables** in Vercel dashboard (`Settings > Environment Variables`).

**Notes:**
- Vercel automatically handles cold starts and scaling
- MCP connections are established on first request
- Redis must be accessible from Vercel (use Upstash or similar)

---

## 🎨 Customization

### Adding Personalities

Create a new file in `prompts/` directory:

```bash
# prompts/expert.txt
You are a technical expert who provides detailed, accurate answers...
```

Switch roles in chat:
```
/role expert
```

### MCP Tool Integration

Configure MCP servers in `.env`:

```bash
MCP_SERVER_1_URL=http://your-mcp-server.com/mcp
MCP_SERVER_1_TOKEN=optional_bearer_token

MCP_SERVER_2_URL=http://another-server.com/mcp
# Add more as needed (MCP_SERVER_3_URL, etc.)
```

The bot will automatically discover and use available tools.

---

## 🤖 Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/clear` | Clear conversation history |
| `/role [name]` | Switch bot personality |
| `/model [name]` | Switch LLM model |
| `/refresh` | Refresh MCP tool list |

---

## 🛠️ Development

### Project Structure

```
lark_bot/
├── api/
│   ├── app.py              # Flask application
│   ├── config.py           # Configuration
│   ├── commands/           # Command handlers
│   └── services/
│       ├── llm_client.py   # LLM API client
│       ├── mcp_service.py  # MCP integration
│       ├── lark_service.py # Lark API
│       └── redis_service.py# Redis operations
├── prompts/                # Bot personalities
├── .env.example           # Environment template
└── vercel.json            # Vercel configuration
```

### Running Tests

```bash
# Syntax check
.venv/bin/python -m py_compile api/**/*.py

# Manual testing
.venv/bin/python -c "from api.app import app; print('✓ App loaded')"
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions welcome! Please feel free to submit pull requests or open issues.

---

## 💡 Tips

- **Low traffic?** Default 5-minute tool refresh is perfect
- **High traffic?** Increase `MCP_TOOLS_REFRESH_INTERVAL` to reduce overhead
- **Tools changing frequently?** Use `/refresh` command or decrease interval
- **Debugging?** Set `DEBUG_MODE=true` for verbose logs

---

Made with ❤️ for the Lark community