# TARS

![TARS](https://raw.githubusercontent.com/b-3llum/tars/main/assets/banner.png)

**Hybrid AI Command Assistant for Cybersecurity Workflows**

![version](https://img.shields.io/badge/version-1.0.0-blue)
![python](https://img.shields.io/badge/python-3.11+-blue)
![platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey)
![license](https://img.shields.io/badge/license-MIT-lightgrey)
![swift](https://img.shields.io/badge/iOS-Swift%205-orange)
---

## Overview

**TARS** is a distributed AI assistant system designed for cybersecurity operators. It combines a local LLM (via Ollama) for fast classification with Claude API for advanced reasoning, all orchestrated through a FastAPI control server and driven from an iOS chat interface.

Every action is whitelisted, audited, and gated behind confirmation for sensitive operations — no raw LLM-generated commands ever reach a shell.

---

## Architecture

```
iPhone (TARS App)
  → FastAPI Control Server (your machine)
    → Decision Engine
       → Ollama (fast: classify, short tasks)
       → Claude API (complex: planning, analysis)
    → Action Engine
       → Local commands (nmap, systemctl, logs)
       → SSH execution (paramiko, key-auth only)
  → Response back to iPhone
```

---

## Modules

```
server/
├── main.py              FastAPI entry point
├── router.py            POST /tars/request, /confirm, GET /health
├── decision_engine.py   Routes simple → Ollama, complex → Claude
├── action_engine.py     Whitelisted command execution
├── llm_local.py         Ollama REST integration
├── llm_claude.py        Anthropic Claude (structured JSON)
├── ssh_manager.py       Paramiko SSH, key-auth, preconfigured hosts
├── security.py          API key auth, rate limiting, input sanitization
├── config.py            Settings loader (.env + YAML)
└── logger.py            Structured audit log (JSONL)

ios/Tars/
├── Models/              Request/Response Codables
├── Network/             URLSession-based NetworkManager
└── Views/               Chat UI with confirmation flow
```

---

## Security Model

| Layer | Implementation |
|---|---|
| Authentication | API key via `X-API-Key` header |
| Input validation | Shell metacharacter stripping, path traversal blocking |
| Command execution | Predefined whitelist templates only — no raw LLM output executed |
| Sensitive actions | Require explicit user confirmation (`/tars/confirm`) |
| SSH | Key-based auth only, preconfigured hosts, `RejectPolicy` |
| Rate limiting | Per-IP, configurable RPM |
| Audit trail | Every action logged to `logs/audit.jsonl` |

---

## Installation

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) running locally with `llama3` or `mistral`
- Anthropic API key

### Setup

```bash
git clone https://github.com/b-3llum/tars ~/tars
cd ~/tars

# Configure
cp .env.example .env
# Edit .env with your TARS_API_KEY and ANTHROPIC_API_KEY

# Install dependencies
pip install -r requirements.txt

# Pull a local model
ollama pull llama3

# Run
python -m server.main
```

The server starts on `http://0.0.0.0:8400`.

---

## iOS App

Open the `ios/` directory in Xcode. Update `NetworkManager.swift` with:
- Your server's LAN IP and port
- The same API key from `.env`

Build and run on your device.

---

## Configuration

### `config/tars.yaml`

- **command_whitelist** — only these command templates can be executed
- **sensitive_actions** — intents that require user confirmation
- **simple_intents** — keywords that route to local LLM instead of Claude

### `config/hosts.yaml`

SSH host definitions with IP, user, and key path. Key-based auth only.

---

## API

| Endpoint | Method | Description |
|---|---|---|
| `/tars/health` | GET | Server + Ollama status |
| `/tars/request` | POST | Send a message, get a plan + result |
| `/tars/confirm` | POST | Confirm or deny a sensitive action |

All endpoints require `X-API-Key` header.

---

## Legal

TARS is designed for use in **authorised** security testing environments and personal lab networks. The operator is responsible for ensuring all targets are within scope and that proper authorisation has been obtained. The author assumes no liability for misuse.
