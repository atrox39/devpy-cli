# DevPy CLI

An intelligent command-line assistant powered by LLM (DeepSeek/OpenAI) to manage Docker environments, both local and remote via SSH. Designed to simplify DevOps tasks with natural language, ensuring security and control.

## Key Features

*   **Natural Language Interaction**: "Restart the nginx container", "Show database logs", "Monitor memory usage".
*   **Local and Remote Docker Management**: Connect to your local machine or remote servers via SSH transparently.
*   **Secure SSH Key Management**: Encrypted storage (AES-256) of SSH private keys. Import from `~/.ssh`.
*   **Granular Permission System**:
    *   Interactive confirmation for critical operations (write/delete).
    *   Configurable whitelists.
    *   Persistent permission rules with hot-reload.
    *   "Dry-Run" mode to simulate executions.
*   **Logging and Auditing**: Detailed logging of all operations and permission decisions in `logs/permissions.log`.

## System Requirements

*   Python 3.11 or higher.
*   Docker client installed (local) or SSH access to a server with Docker.
*   Operating System: Windows, macOS, Linux.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repo-url>
    cd devpy-cli
    ```

2.  **Create virtual environment (recommended):**

    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -e .
    ```

4.  **Configure environment:**
    Create a `.env` file in the root (you can copy the example if it exists) with your LLM API key:

    ```ini
    DEEPSEEK_API_KEY=your_api_key_here
    # Optional: LLM=chatgpt and OPENAI_API_KEY=...
    ```

## Usage Guide

### Start the CLI

```bash
# From the repository
python app.py

# Or if installed in editable mode
devpy-cli
```

On first run, if no `.env` file exists, an interactive setup wizard will guide you through:
- Choosing your LLM provider.
- Entering the API key.
- Optionally setting a custom base URL.

After setup, the CLI banner appears and you are asked whether to enable dry-run mode.

---

### CLI Mode (Local Docker)

Use this mode when you want to manage containers running on the same machine where DevPy CLI is installed.

- **Requirements**
  - Docker is installed and the daemon is running locally.
  - Your user can talk to the Docker socket (e.g., `docker ps` works from your shell).

- **Step-by-step**
  1. Start the CLI (see above).
  2. When prompted, choose whether to enable dry-run mode.
  3. Ensure the mode is set to `local` (this is the default):
     ```bash
     config mode local
     ```
  4. Type natural language instructions, for example:
     - `What containers are running?`
     - `Restart the nginx container and show me its latest logs`
     - `Create a redis container called cache`
  5. When an action is potentially destructive (creating/stopping/removing containers, starting monitors, etc.), DevPy will:
     - Show a preview of the Docker command.
     - Ask for confirmation (once, for the command, or for the whole session).

- **Typical local use cases**
  - Quickly inspecting and restarting local services from the terminal.
  - Checking logs of a misbehaving container.
  - Spinning up utility containers (e.g., Redis, Postgres) by name and image.

---

### SSH Mode (Remote Docker over SSH)

Use this mode to manage containers on a remote host over SSH, while still talking to the CLI locally.

- **Prerequisites**
  - The remote server:
    - Has Docker installed and running.
    - Is reachable via SSH (e.g., `ssh user@host` works).
  - You have an SSH private key that can authenticate to that server.

- **Step 1: Store your SSH key (encrypted)**

  You can import keys from `~/.ssh` or add a specific file:

  ```bash
  # Scan ~/.ssh for potential keys and import one
  keys scan

  # Or add a specific key path
  keys add my-remote /path/to/id_rsa

  # List stored keys
  keys list
  ```

  During `keys scan` or `keys add`, you are asked for a **passphrase for encryption**.  
  This passphrase is used to derive a key that encrypts your private key on disk (AES-256 via `cryptography.Fernet`).

- **Step 2: Configure SSH connection**

  In the CLI, run:

  ```bash
  config ssh
  ```

  You will be prompted for:
  - **SSH Host** (e.g., `myserver.example.com` or `192.168.1.100`)
  - **SSH User** (e.g., `ubuntu`, `root`, `deploy`)
  - **SSH Key Name** (one of the names returned by `keys list`)

  This information is stored in `config.json`.

- **Step 3: Switch to SSH mode**

  ```bash
  config mode ssh
  ```

  From now on, Docker operations happen against the remote host using the stored SSH configuration.

- **Step 4: Authenticate with your key**

  When the backend needs to connect to the remote Docker daemon, it:
  - Prompts for the passphrase you used when storing the key, **or**
  - Uses the `DOCKER_SSH_PASSPHRASE` environment variable if it is set.

  This decrypted key is written to a temporary file (with restricted permissions) and used only for the SSH connection.

- **Typical SSH use cases**
  - Managing a remote Docker host from your laptop without logging in manually.
  - Checking logs and restarting containers in staging/production environments.
  - Monitoring memory usage of remote containers and triggering alerts.

---

### Command Reference

#### Configuration Commands

Use these to configure how the CLI connects and which LLM it uses:

```bash
# Show or set connection mode
config mode           # shows current mode (local or ssh)
config mode local     # use local Docker
config mode ssh       # use remote Docker over SSH

# Configure SSH details (host, user, key)
config ssh

# Re-run the LLM setup wizard and regenerate .env
config llm
```

#### SSH Key Management Commands

```bash
# Import keys from ~/.ssh (interactive)
keys scan

# Add a key manually
keys add <name> <path_to_private_key>

# List saved keys
keys list

# Delete a stored key
keys delete <name>
```

#### Permission Management Commands

Control what the agent is allowed to do:

```bash
# View current rules
permissions list

# Block container restarts permanently
permissions add restart_container deny

# Allow container creation (with optional parameters)
permissions add create_container allow

# Reset all persistent permission rules
permissions reset
```

During interactive confirmations, you can choose:
- `y`  – allow once.
- `yc` – always allow this exact command during the session.
- `ys` – always allow this operation type during the session.
- `n`  – deny.

---

### Interaction Examples with the Agent

Once configured, simply type what you need:

- *"What containers are running?"*
- *"Restart the 'web-app' container and show me its latest logs"*
- *"Create a redis container named 'my-redis'"*
- *"Alert me if memory usage of container 'api' exceeds 80%"*

The agent plans and executes one or more Docker operations, asking for permission when necessary.

---

### Dry-Run Mode

You can enable dry-run mode in two ways:

- At startup, when the CLI asks:
  - Answer `y` to run in dry-run mode for the session.
- Via environment variable:
  - Set `DRY_RUN=1` before starting the app.

In this mode, the agent **simulates** write actions (creating, deleting, restarting containers, starting monitors, etc.) without actually executing them.  
The permission log still records what *would* have been executed.

---

## Authentication and Security

- **LLM API Authentication**
  - The `.env` file created by the setup wizard stores:
    - `LLM` – which provider/adapter to use.
    - `<PROVIDER>_API_KEY` – the API key for that provider.
    - Optionally `LLM_BASE_URL` – custom base URL for compatible providers.
  - You can re-run the wizard at any time with:
    ```bash
    config llm
    ```

- **SSH Key Encryption**
  - Stored SSH keys live in `ssh_keys.enc`.
  - Each key is encrypted using a passphrase-derived key (PBKDF2 + AES-256).
  - The file permissions are hardened to allow read/write only for the current user.

- **Runtime Environment Variables**
  - `DRY_RUN` – if set to `1`, `true`, `yes`, or `y`, forces dry-run mode.
  - `DOCKER_SSH_PASSPHRASE` – optional; if set, avoids interactive passphrase prompts for SSH keys.
  - `DOCKER_SAFE_COMMANDS` – comma-separated list of operations that never prompt for confirmation.
  - `DOCKER_CLI_USER` – overrides the username recorded in permission logs.

- **Logging and Auditing**
  - All operations go through a permission and logging layer.
  - Logs are written as JSON lines to `logs/permissions.log`.
  - Each entry includes timestamp, user, operation, arguments, decision, and optional command preview.

## Project Structure

*   `app.py`: Entry point.
*   `frontend_cli.py`: User interface and CLI command handling.
*   `backend.py`: Agent logic, integration with LangChain/LangGraph and Docker tools.
*   `permissions_manager.py`: Access control and auditing system.
*   `ssh_key_manager.py`: Encryption and key management.
*   `config_manager.py`: Configuration persistence (mode, ssh host).
*   `logs/`: Audit log files.

## License

MIT License. See `LICENSE` file for more details.

## Author

Developed by atrox39.
