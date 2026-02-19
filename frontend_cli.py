import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import json
import urllib.request
import tomllib
from rich.console import Console
from rich.prompt import Prompt
from rich.markdown import Markdown
from backend import run_agent_flow, config_manager, ssh_key_manager, reset_docker_client, permission_manager
from setup_wizard import run_setup

console = Console()


def get_cli_version():
  try:
    return version('devpy-cli')
  except PackageNotFoundError:
    pass

  try:
    root = Path(__file__).resolve().parent
    pyproject_path = root / 'pyproject.toml'
    if pyproject_path.exists():
      data = tomllib.loads(pyproject_path.read_text(encoding='utf-8'))
      project = data.get('project') or {}
      value = project.get('version')
      if isinstance(value, str) and value:
        return value
  except Exception:
    pass

  return 'unknown'


def fetch_latest_version():
  try:
    with urllib.request.urlopen('https://pypi.org/pypi/devpy-cli/json', timeout=2) as resp:
      if resp.status != 200:
        return None
      data = json.loads(resp.read().decode('utf-8'))
      info = data.get('info') or {}
      value = info.get('version')
      if isinstance(value, str) and value:
        return value
  except Exception:
    return None


def normalize_version(value):
  parts = []
  for part in str(value).split('.'):
    try:
      parts.append(int(part))
    except ValueError:
      break
  return tuple(parts)


def check_for_update():
  current = get_cli_version()
  latest = fetch_latest_version()
  if not current or current == 'unknown' or not latest:
    return
  cur_tuple = normalize_version(current)
  lat_tuple = normalize_version(latest)
  if not cur_tuple or not lat_tuple:
    return
  if cur_tuple < lat_tuple:
    console.print(f'[yellow]A new version of DevPy CLI is available: {latest} (you have {current}).[/yellow]')
    console.print('[dim]Update with: pip install -U devpy-cli[/dim]')


def handle_config_command(user_input):
  parts = user_input.split()
  if len(parts) < 2:
    console.print('[yellow]Usage: config [mode|ssh|llm][/yellow]')
    return

  cmd = parts[1]
  if cmd == 'mode':
    if len(parts) == 3:
      new_mode = parts[2]
      if new_mode in ['local', 'ssh']:
        config_manager.set_mode(new_mode)
        reset_docker_client()
        console.print(f'[green]Mode set to {new_mode}[/green]')
      else:
        console.print("[red]Invalid mode. Use 'local' or 'ssh'[/red]")
    else:
      console.print(f'Current mode: {config_manager.get_mode()}')
  elif cmd == 'ssh':
    host = Prompt.ask('SSH Host')
    user = Prompt.ask('SSH User')
    keys = ssh_key_manager.list_keys()
    if not keys:
      console.print("[red]No SSH keys found. Add one with 'keys add' first.[/red]")
      return
    key_name = Prompt.ask('SSH Key Name', choices=keys)
    config_manager.set_ssh_config(host, user, key_name)
    reset_docker_client()
    console.print('[green]SSH Configuration saved.[/green]')
  elif cmd == 'llm':
    console.print('[bold]Reconfiguring LLM Settings...[/bold]')
    run_setup(force=True)
    console.print('[yellow]Please restart the application for changes to take effect.[/yellow]')


def handle_keys_command(user_input):
  parts = user_input.split()
  if len(parts) < 2:
    console.print('[yellow]Usage: keys [list|add|delete|scan][/yellow]')
    return

  cmd = parts[1]
  if cmd == 'list':
    keys = ssh_key_manager.list_keys()
    if keys:
      console.print('Stored SSH Keys:')
      for k in keys:
        console.print(f'- {k}')
    else:
      console.print('No keys stored.')
  elif cmd == 'scan':
    # List keys in ~/.ssh
    ssh_dir = Path.home() / '.ssh'
    if not ssh_dir.exists():
      console.print(f'[red]Directory {ssh_dir} not found.[/red]')
      return

    potential_keys = []
    for f in ssh_dir.iterdir():
      if (
        f.is_file()
        and not f.name.endswith('.pub')
        and not f.name.startswith('known_hosts')
        and not f.name.startswith('config')
      ):
        potential_keys.append(f)

    if not potential_keys:
      console.print(f'[yellow]No potential keys found in {ssh_dir}[/yellow]')
      return

    console.print(f'[bold]Found keys in {ssh_dir}:[/bold]')
    choices = [k.name for k in potential_keys]
    choices.append('Cancel')

    selected = Prompt.ask('Select key to import', choices=choices, default='Cancel')
    if selected == 'Cancel':
      return

    path = ssh_dir / selected
    name = Prompt.ask('Enter name for this key', default=selected)
    passphrase = Prompt.ask('Enter Passphrase for encryption', password=True)

    try:
      ssh_key_manager.add_key(name, str(path), passphrase)
      console.print(f"[green]Key '{name}' imported successfully.[/green]")
    except Exception as e:
      console.print(f'[red]Error adding key: {e}[/red]')

  elif cmd == 'add':
    if len(parts) < 4:
      console.print('[yellow]Usage: keys add <name> <path>[/yellow]')
      return
    name = parts[2]
    path = parts[3]
    passphrase = Prompt.ask('Enter Passphrase for encryption', password=True)
    try:
      ssh_key_manager.add_key(name, path, passphrase)
      console.print(f"[green]Key '{name}' added successfully.[/green]")
    except Exception as e:
      console.print(f'[red]Error adding key: {e}[/red]')
  elif cmd == 'delete':
    if len(parts) < 3:
      console.print('[yellow]Usage: keys delete <name>[/yellow]')
      return
    name = parts[2]
    if ssh_key_manager.delete_key(name):
      console.print(f"[green]Key '{name}' deleted.[/green]")
    else:
      console.print(f"[red]Key '{name}' not found.[/red]")


def handle_permissions_command(user_input):
  parts = user_input.split()
  if len(parts) < 2:
    console.print('[yellow]Usage: permissions [list|add|reset][/yellow]')
    return

  cmd = parts[1]
  manager = permission_manager.config_manager

  if cmd == 'list':
    rules = manager.list_rules()
    if not rules:
      console.print('No permission rules configured.')
    else:
      console.print('[bold]Permission Rules:[/bold]')
      for rule in rules:
        console.print(f'- {rule["operation"]} -> {rule["decision"]} (Params: {rule.get("params")})')

  elif cmd == 'add':
    # Interactive add
    # permissions add <operation> <decision> [param=value]
    if len(parts) < 4:
      console.print('[yellow]Usage: permissions add <operation> <allow|deny> [param=value...][/yellow]')
      return

    operation = parts[2]
    decision = parts[3]
    if decision not in ['allow', 'deny']:
      console.print("[red]Decision must be 'allow' or 'deny'[/red]")
      return

    params = {}
    if len(parts) > 4:
      for p in parts[4:]:
        if '=' in p:
          k, v = p.split('=', 1)
          params[k] = v

    manager.add_rule(operation, decision, params=params)
    console.print(f'[green]Rule added for {operation} -> {decision}[/green]')

  elif cmd == 'reset':
    if Prompt.ask('Are you sure you want to reset all permission rules?', choices=['y', 'n']) == 'y':
      manager.reset_config()
      console.print('[green]Permissions configuration reset.[/green]')


def run_cli():
  console.print(Markdown('# DevPy CLI'))
  console.print(f'[dim]Version {get_cli_version()}[/dim]\n')
  check_for_update()
  dry_run_answer = Prompt.ask(
    '\n[bold]Enable dry-run mode?[/bold]',
    choices=['y', 'n'],
    default='n',
  )
  if dry_run_answer == 'y':
    os.environ['DRY_RUN'] = '1'
  while True:
    try:
      user_input = Prompt.ask('\n[bold]Enter a command[/bold]')
      if user_input.lower() in ['exit', 'quit', 'bye']:
        console.print('\n[bold green]Goodbye[/bold green]')
        break
      if user_input.strip() == '':
        continue

      if user_input.startswith('config'):
        handle_config_command(user_input)
        continue

      if user_input.startswith('keys'):
        handle_keys_command(user_input)
        continue

      if user_input.startswith('permissions'):
        handle_permissions_command(user_input)
        continue

      run_agent_flow(user_input)
    except KeyboardInterrupt:
      console.print('\n[bold green]Goodbye[/bold green]')
      break
