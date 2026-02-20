# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.4] - 2026-02-19

### Added
- Multi-provider LLM support: DevPy CLI can now run with Anthropic Claude, Google Gemini, and local Ollama/OpenWebUI backends in addition to the existing DeepSeek and OpenAI integrations. Each provider is wrapped in a dedicated adapter under the `llm/` package and selected via the `LLM` environment variable.
- OpenWebUI/Ollama compatibility layer: introduced an Ollama adapter that speaks the OpenAI-compatible HTTP API, allowing DevPy to connect directly to Ollama or OpenWebUI using configurable base URLs and models.


## [1.0.3] - 2026-02-19

### Fixed
- Container creation now correctly handles missing images. When `create_container` is called with an image that is not yet present locally, it will automatically pull the image using the new `download_image` tool before creating and starting the container. This prevents runtime errors during first-time deployments that reference images not previously pulled. See backend implementation in [backend.py](file:///c:/Users/cortega/Development/python/devops/backend.py#L236-L280).
- Added a safe Docker image deletion tool. The new `delete_image` backend function checks whether the image exists and wraps `docker image remove` behind the permission system, returning clear messages when the image is missing instead of raising unhandled exceptions. See [backend.py](file:///c:/Users/cortega/Development/python/devops/backend.py#L411-L436).

## [1.0.2] - 2026-02-19

### Added
- Dynamic CLI version display: DevPy CLI now reads its version from the installed package metadata or `pyproject.toml`, so the banner always reflects the current release without hardcoding it in `frontend_cli.py`.
- Version update check: on startup, the CLI queries PyPI for the latest `devpy-cli` version and, if a newer release is available, shows a non-intrusive notice with the recommended `pip install -U devpy-cli` command.

## [1.0.1] - 2026-02-19

### Fixed
- Packaging: included missing modules so the installed `devpy-cli` script no longer fails at startup.
  - Added `setup_wizard` to packaged modules to avoid `ImportError` on first run when `.env` is not present. See [pyproject.toml](file:///c:/Users/cortega/Development/python/devops/pyproject.toml#L39-L48).
  - Packaged `llm` directory and added `llm/__init__.py` so imports like `from llm.deepseek import llm` work in the installed environment. See [pyproject.toml](file:///c:/Users/cortega/Development/python/devops/pyproject.toml#L39-L48).
  - Result: fixes `ModuleNotFoundError: No module named 'llm'` and ensures the setup wizard loads correctly when `devpy-cli` runs.

## [1.0.0] - 2026-02-19

### Security
- **Command Injection Prevention**: Implemented strict input sanitization for `docker exec` commands to prevent unauthorized shell command chaining or substitution.
- **Sensitive File Hardening**: The setup wizard and key manager now automatically apply restrictive file permissions (read/write only for owner) to `.env` (API Keys) and `ssh_keys.enc` (Encrypted SSH Keys) to prevent unauthorized access in multi-user environments.
- **Dependency Pinning**: Updated `pyproject.toml` to use pinned versions for all core dependencies (`docker`, `paramiko`, `cryptography`, etc.), mitigating supply chain risks and ensuring reproducible builds.

### Added
- **Interactive Setup Wizard**: New first-run experience that guides users through configuring LLM providers (DeepSeek, OpenAI, etc.) and API keys securely.
- **SSH Key Management**: Secure storage for SSH private keys using AES-256 encryption. Support for importing keys from `~/.ssh`.
- **Granular Permission System**:
    - Interactive confirmation for critical operations (create, delete, restart containers).
    - Persistent permission rules configuration via `permissions_config.json`.
    - "Dry-Run" mode to simulate actions without execution.
- **Performance Monitoring**: Real-time logging of operation duration to detect latency issues in LLM or Docker connections.
- **Security Audit Tool**: Included `security_audit.py` script to verify system configuration and file permissions.

### Changed
- **Project Rename**: Renamed application from `devops-cli` to `devpy-cli`.
- **Improved Logging**: Audit logs (`logs/permissions.log`) now include detailed execution context and performance metrics.
