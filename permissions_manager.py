import os
import json
import getpass
import time
from datetime import datetime
from pathlib import Path
from permissions_config_manager import PermissionConfigManager


class PermissionDecision:
  ALLOW_ONCE = 'allow_once'
  ALLOW_COMMAND = 'allow_command'
  ALLOW_SESSION = 'allow_session'
  DENY = 'deny'


class PermissionManager:
  def __init__(self, whitelist=None, dry_run=None, user=None, log_file=None):
    env_whitelist = os.getenv('DOCKER_SAFE_COMMANDS')
    env_set = set()
    if env_whitelist:
      for item in env_whitelist.split(','):
        value = item.strip()
        if value:
          env_set.add(value)
    if whitelist is None:
      whitelist = env_set
    else:
      whitelist = set(whitelist) | env_set
    self.whitelist = whitelist
    if dry_run is None:
      env_dry = os.getenv('DRY_RUN', '').lower()
      self.dry_run = env_dry in {'1', 'true', 'yes', 'y'}
    else:
      self.dry_run = dry_run
    if user is None:
      env_user = os.getenv('DOCKER_CLI_USER')
      if env_user:
        self.user = env_user
      else:
        try:
          self.user = getpass.getuser()
        except Exception:
          self.user = 'unknown'
    else:
      self.user = user
    logs_dir = Path('logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    if log_file is None:
      self.log_file = logs_dir / 'permissions.log'
    else:
      self.log_file = Path(log_file)
      self.log_file.parent.mkdir(parents=True, exist_ok=True)
    self.session_approvals = {'session': set(), 'command': set()}

    # Initialize Persistent Config Manager
    self.config_manager = PermissionConfigManager()

  def classify_operation(self, operation):
    read_ops = {
      'list_containers',
      'get_logs',
      'inspect_container',
      'list_images',
      'list_volumes',
      'list_networks',
      'check_resource',
    }
    if operation in read_ops:
      return 'read'
    return 'write'

  def needs_confirmation(self, operation, command_key=None):
    if operation in self.whitelist:
      return False
    if operation in self.session_approvals['session']:
      return False
    if command_key and command_key in self.session_approvals['command']:
      return False

    # Check persistent config
    persistent_decision = self.config_manager.get_decision(operation)
    if persistent_decision == 'allow':
      return False

    classification = self.classify_operation(operation)
    return classification == 'write'

  def record_approval_for_command(self, command_key):
    if command_key:
      self.session_approvals['command'].add(command_key)

  def record_approval_for_session(self, operation):
    self.session_approvals['session'].add(operation)

  def log_action(self, operation, args, decision, effective_dry_run, command_preview, impact, duration_ms=0):
    entry = {
      'timestamp': datetime.utcnow().isoformat() + 'Z',
      'user': self.user,
      'operation': operation,
      'args': args or {},
      'decision': decision,
      'dry_run': effective_dry_run,
      'command_preview': command_preview,
      'impact': impact,
      'duration_ms': duration_ms,
    }
    try:
      with self.log_file.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
      pass

  def execute(
    self,
    operation,
    fn,
    fn_args=None,
    fn_kwargs=None,
    command_preview=None,
    impact=None,
    command_key=None,
    prompt_func=None,
    decision_override=None,
  ):
    start_time = time.time()
    if fn_args is None:
      fn_args = ()
    if fn_kwargs is None:
      fn_kwargs = {}
    args_snapshot = {'args': list(fn_args), 'kwargs': fn_kwargs}
    effective_dry_run = self.dry_run

    # Check if denied by persistent config first (priority system)
    persistent_decision = self.config_manager.get_decision(operation)
    if persistent_decision == 'deny':
      duration = (time.time() - start_time) * 1000
      self.log_action(
        operation, args_snapshot, 'denied_by_config', effective_dry_run, command_preview, impact, duration
      )
      return 'Operación denegada por configuración persistente'

    decision = PermissionDecision.ALLOW_ONCE
    if self.needs_confirmation(operation, command_key):
      if decision_override is not None:
        decision = decision_override
      elif prompt_func is not None:
        decision = prompt_func(operation, impact, command_preview)
      else:
        decision = PermissionDecision.DENY

      if decision == PermissionDecision.DENY:
        duration = (time.time() - start_time) * 1000
        self.log_action(operation, args_snapshot, 'denied', effective_dry_run, command_preview, impact, duration)
        return 'Operación cancelada por el usuario'
      if decision == PermissionDecision.ALLOW_COMMAND:
        self.record_approval_for_command(command_key)
      if decision == PermissionDecision.ALLOW_SESSION:
        self.record_approval_for_session(operation)

    if effective_dry_run:
      duration = (time.time() - start_time) * 1000
      self.log_action(operation, args_snapshot, 'allowed_dry_run', True, command_preview, impact, duration)
      return f'Modo dry-run: se ejecutaría {command_preview}'

    try:
      result = fn(*fn_args, **fn_kwargs)
      duration = (time.time() - start_time) * 1000
      self.log_action(operation, args_snapshot, 'allowed', False, command_preview, impact, duration)
      return result
    except Exception as e:
      duration = (time.time() - start_time) * 1000
      self.log_action(operation, args_snapshot, f'error: {str(e)}', False, command_preview, impact, duration)
      raise e
