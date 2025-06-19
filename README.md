# Lark AI Bot

A powerful, configurable, and ready-to-deploy AI assistant for the Lark (Feishu) platform. This bot integrates with OpenAI's models to provide intelligent responses, supports customizable personalities, and is built with a modern, container-based architecture for easy deployment and scaling.

## ✨ Features

- **Intelligent Conversation**: Powered by OpenAI's language models to understand and respond to user queries.
- **Customizable Personalities (Roles)**: Easily define multiple bot personalities (e.g., "expert," "doctor") by simply adding text files to the `prompts/` directory.
- **Rich Text Responses**: The bot is instructed to use Lark's formatting options (bold, italics, colors, links) to provide clear and engaging answers.
- **Conversation Memory**: Utilizes Redis/Valkey to maintain conversation context, allowing for follow-up questions.
- **Smart Response Logic**:
    - In **group chats**, the bot will only respond when explicitly mentioned (`@`).
    - In **private (P2P) chats**, the bot will respond to all messages.
- **Debug Mode**: An optional debug mode that provides verbose logging of incoming requests and AI responses for easy troubleshooting.
- **Containerized Deployment**: Comes with a `Dockerfile` and `docker-compose.yml` for easy local setup and production deployment.
- **Automated CI/CD**: Includes a GitHub Actions workflow (`.github/workflows/docker-publish.yml`) to automatically build and publish the Docker image to container registries.

## 🚀 Getting Started (Local Development)

You can get the entire application stack running locally with a single command using Docker Compose.

### Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

### 1. Configure Environment Variables

First, create a `.env` file by copying the example file:

```bash
cp .env.example .env
```

Now, open the `.env` file and fill in the required values.

| Variable                  | Description                                                                                             |
| ------------------------- | ------------------------------------------------------------------------------------------------------- |
| `LARK_APP_ID`             | **Required.** Your Lark application's App ID.                                                           |
| `LARK_APP_SECRET`         | **Required.** Your Lark application's App Secret.                                                       |
| `LARK_VERIFICATION_TOKEN` | **Required.** The verification token from your Lark app's event subscription settings.                  |
| `OPENAI_API_KEY`          | **Required.** Your API key for the OpenAI service.                                                      |
| `OPENAI_BASE_URL`         | The base URL for the OpenAI API. Defaults to the official OpenAI URL if not set.                        |
| `REDIS_URL`               | The connection URL for your Redis/Valkey instance. **Note:** This is ignored when using `docker-compose`. |
| `DEFAULT_ROLE`            | The default role to use if none is set. Defaults to `default`.                                          |
| `DEBUG_MODE`              | Set to `true` to enable verbose logging for debugging. Defaults to `false`.                             |

### 2. Run with Docker Compose

With your `.env` file configured, start the application and the Valkey database:

```bash
docker-compose up --build
```

The application will be available at `http://localhost:5001`.

## 🎨 Customizing Roles

You can easily add new personalities or "roles" to the bot.

1.  Create a new `.txt` file in the `prompts/` directory (e.g., `prompts/comedian.txt`).
2.  Write the system prompt for the new role inside this file. This text will define the bot's personality and behavior.
3.  In a chat with the bot, you can now switch to this new role by typing `/role comedian`.

## 🚢 Deployment & CI/CD

This project is configured for automated container builds and publishing via GitHub Actions.

### Dockerfile

The `Dockerfile` uses a modern, multi-stage build process with `uv` to create a lightweight, production-ready image. It runs the application using the `gunicorn` WSGI server.

### GitHub Actions Workflow

The workflow is defined in `.github/workflows/docker-publish.yml` and performs the following actions on every push to the `main` branch:

1.  **Builds** a new Docker image.
2.  **Tags** the image with the commit SHA and `latest`.
3.  **Pushes** the image to container registries based on your repository configuration.

To enable pushing, you need to configure secrets and variables in your GitHub repository's settings (`Settings > Secrets and variables > Actions`):

- **To push to an external registry (e.g., Docker Hub):**
    - `DOCKER_REGISTRY`: (Secret) The URL of the registry (e.g., `docker.io`).
    - `DOCKER_USERNAME`: (Secret) Your username for the registry.
    - `DOCKER_PASSWORD`: (Secret) Your password or access token for the registry.

- **To push to GitHub Container Registry (GHCR):**
    - `PUSH_TO_GHCR`: (Variable) Set the value to `true`.

If the required secrets/variables are not set, the corresponding push step will be skipped.

## 🤖 Available Commands

| Command                 | Description                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------- |
| `/help`                 | Displays the help message, including available commands and the current role.                           |
| `/role [role_name]`     | Switches the bot's personality. If `[role_name]` is omitted, it displays the currently active role.      |
| `/model [model_name]`   | Switches the OpenAI model. If `[model_name]` is omitted, it displays the currently active model.        |
| `/clear`                | Clears the conversation history for the current chat, giving you a fresh start.                         |