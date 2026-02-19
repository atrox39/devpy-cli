# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-05-23

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
