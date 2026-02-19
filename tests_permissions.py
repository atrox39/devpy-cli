import os
import unittest
from pathlib import Path
from permissions_manager import PermissionManager, PermissionDecision


class DummyAction:
  def __init__(self):
    self.calls = 0

  def __call__(self):
    self.calls += 1
    return 'ok'


class PermissionManagerTests(unittest.TestCase):
  def setUp(self):
    log_path = Path('logs_test') / 'test_permissions.log'
    if log_path.exists():
      log_path.unlink()
    self.manager = PermissionManager(
      whitelist=set(),
      dry_run=False,
      user='test',
      log_file=str(log_path),
    )

  def test_write_operation_denied_without_confirmation(self):
    action = DummyAction()
    result = self.manager.execute(
      operation='restart_container',
      fn=action,
      command_preview='docker restart test',
      impact='test',
      command_key='restart:test',
      decision_override=PermissionDecision.DENY,
    )
    self.assertEqual(action.calls, 0)
    self.assertIn('cancelada', result)

  def test_write_operation_allowed_with_confirmation(self):
    action = DummyAction()
    result = self.manager.execute(
      operation='restart_container',
      fn=action,
      command_preview='docker restart test',
      impact='test',
      command_key='restart:test',
      decision_override=PermissionDecision.ALLOW_ONCE,
    )
    self.assertEqual(action.calls, 1)
    self.assertEqual(result, 'ok')

  def test_dry_run_does_not_call_action(self):
    log_path = Path('logs_test') / 'test_permissions_dry.log'
    if log_path.exists():
      log_path.unlink()
    manager = PermissionManager(
      whitelist=set(),
      dry_run=True,
      user='test',
      log_file=str(log_path),
    )
    action = DummyAction()
    result = manager.execute(
      operation='restart_container',
      fn=action,
      command_preview='docker restart test',
      impact='test',
      command_key='restart:test',
      decision_override=PermissionDecision.ALLOW_ONCE,
    )
    self.assertEqual(action.calls, 0)
    self.assertIn('dry-run', result)

  def test_read_operation_does_not_require_confirmation(self):
    action = DummyAction()
    result = self.manager.execute(
      operation='list_containers',
      fn=action,
      command_preview='docker ps',
      impact='read',
      command_key='ps',
    )
    self.assertEqual(action.calls, 1)
    self.assertEqual(result, 'ok')

  def test_whitelist_skips_confirmation(self):
    manager = PermissionManager(
      whitelist={'restart_container'},
      dry_run=False,
      user='test',
      log_file=str(Path('logs_test') / 'test_permissions_whitelist.log'),
    )
    action = DummyAction()
    result = manager.execute(
      operation='restart_container',
      fn=action,
      command_preview='docker restart test',
      impact='test',
      command_key='restart:test',
    )
    self.assertEqual(action.calls, 1)
    self.assertEqual(result, 'ok')


if __name__ == '__main__':
  unittest.main()

