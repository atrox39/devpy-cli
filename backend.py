import os
import threading
import psutil
import docker
import time
import tempfile
import atexit
import re
from docker.transport import SSHHTTPAdapter
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from permissions_manager import PermissionManager, PermissionDecision
from config_manager import ConfigManager
from ssh_key_manager import SSHKeyManager

load_dotenv()

console = Console()

config_manager = ConfigManager()
ssh_key_manager = SSHKeyManager()
_docker_client = None
_ssh_temp_key_path = None


def cleanup_temp_key():
  global _ssh_temp_key_path
  if _ssh_temp_key_path and os.path.exists(_ssh_temp_key_path):
    try:
      os.remove(_ssh_temp_key_path)
    except Exception:
      pass


atexit.register(cleanup_temp_key)


class CustomSSHAdapter(SSHHTTPAdapter):
  def __init__(self, base_url, key_filename, **kwargs):
    self.key_filename = key_filename
    super().__init__(base_url, **kwargs)

  def _create_paramiko_client(self, base_url):
    super()._create_paramiko_client(base_url)
    if self.key_filename:
      self.ssh_params['key_filename'] = self.key_filename


def reset_docker_client():
  global _docker_client
  if _docker_client:
    try:
      _docker_client.close()
    except Exception:
      pass
  _docker_client = None
  cleanup_temp_key()


def get_docker_client():
  global _docker_client, _ssh_temp_key_path
  if _docker_client:
    return _docker_client

  mode = config_manager.get_mode()
  if mode == 'local':
    try:
      _docker_client = docker.from_env()
    except Exception as e:
      console.print(f'[bold red]Error initializing local Docker client: {e}[/bold red]')
      # Return a dummy client or let it fail later?
      # Better to raise, but tools might need handling.
      raise e
  else:
    ssh_config = config_manager.get_ssh_config()
    host = ssh_config.get('host')
    user = ssh_config.get('user')
    key_name = ssh_config.get('key_name')

    if not host or not user or not key_name:
      console.print('[bold red]SSH configuration incomplete. Please configure SSH settings.[/bold red]')
      raise ValueError('SSH configuration incomplete')

    # Get Passphrase
    passphrase = os.getenv('DOCKER_SSH_PASSPHRASE')
    if not passphrase:
      from rich.prompt import Prompt

      passphrase = Prompt.ask(f"Enter passphrase for key '{key_name}'", password=True)

    try:
      private_key_content = ssh_key_manager.get_key(key_name, passphrase)
    except Exception as e:
      console.print(f'[bold red]Failed to load SSH key: {e}[/bold red]')
      raise e

    # Create temp file for the key
    # We need to close it so paramiko can open it by name
    tf = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
    tf.write(private_key_content)
    tf.close()
    _ssh_temp_key_path = tf.name

    ssh_url = f'ssh://{user}@{host}'

    try:
      # Create SSH Adapter
      ssh_adapter = CustomSSHAdapter(ssh_url, key_filename=_ssh_temp_key_path)

      # Create API Client
      api_client = docker.APIClient(base_url='http://localhost', version='auto')
      api_client.mount('http+docker://ssh', ssh_adapter)
      api_client.base_url = 'http+docker://ssh'

      # Create Docker Client
      client = docker.DockerClient(version='auto')
      client.api = api_client
      _docker_client = client
    except Exception as e:
      cleanup_temp_key()
      console.print(f'[bold red]Error connecting to remote Docker: {e}[/bold red]')
      raise e

  return _docker_client


global_config = {'configurable': {'thread_id': 'prinsipal_devops'}}

permission_manager = PermissionManager()


def build_command_preview(parts):
  return ' '.join(str(p) for p in parts)


def permission_prompt(operation, impact, command_preview):
  console.print('\n[bold yellow]Permission Required[/bold yellow]')
  console.print(f'Operation: {operation}')
  if impact:
    console.print(f'Potential Impact: {impact}')
  if command_preview:
    console.print(f'Command: {command_preview}')
  console.print('Options: (y) yes, (n) no, (yc) yes for command, (ys) yes for session')
  from rich.prompt import Prompt

  answer = Prompt.ask('(y/n/yc/ys)', choices=['y', 'n', 'yc', 'ys'], default='n')
  if answer == 'y':
    return PermissionDecision.ALLOW_ONCE
  if answer == 'yc':
    return PermissionDecision.ALLOW_COMMAND
  if answer == 'ys':
    return PermissionDecision.ALLOW_SESSION
  return PermissionDecision.DENY


@tool
def check_resource() -> str:
  """Shows system CPU, memory, and disk usage"""
  # For remote docker, psutil runs on LOCAL machine.
  # If we want remote stats, we should use a container or docker stats?
  # The user asked for "Remote Docker execution".
  # check_resource using psutil checks LOCAL resource.
  # This might be intended or not. If we want remote host stats, we can't easily get them via docker API except via a container.
  # I'll keep it local for now as psutil is local.
  cpu = psutil.cpu_percent(interval=1)
  memory = psutil.virtual_memory()
  disk = psutil.disk_usage('/')
  return f'CPU: {cpu}%, Memory: {memory.percent}%, Disk: {disk.percent}%'


@tool
def get_docker_logs(container_name: str, tail: int = 50) -> str:
  """Gets the last logs of a Docker container"""
  try:
    client = get_docker_client()
    container = client.containers.get(container_name)
    logs = container.logs(tail=tail).decode('utf-8')
    return f'Logs for container {container_name}:\n{logs[-2000:]}'
  except docker.errors.NotFound:
    return f'Error: Container {container_name} not found'
  except Exception as e:
    return f'Error: {str(e)}'


@tool
def list_containers() -> str:
  """Lists active Docker containers with their status"""
  try:
    client = get_docker_client()
    containers = client.containers.list()
    return '\n'.join([f'{c.name} ({c.status})' for c in containers])
  except Exception as e:
    return f'Error listing containers: {e}'


@tool
def inspect_container(container_name: str) -> str:
  """Inspects a Docker container and returns its attributes"""
  try:
    client = get_docker_client()
    container = client.containers.get(container_name)
    return str(container.attrs)
  except docker.errors.NotFound:
    return f'Error: Container {container_name} not found'
  except Exception as e:
    return f'Error: {str(e)}'


@tool
def restart_docker_container(container_name: str) -> str:
  """Restarts a specified Docker container"""
  command_preview = build_command_preview(['docker', 'restart', container_name])

  def action():
    client = get_docker_client()
    container = client.containers.get(container_name)
    container.restart()
    return f'Container {container_name} restarted'

  return permission_manager.execute(
    operation='restart_container',
    fn=action,
    fn_kwargs={},
    command_preview=command_preview,
    impact='Restarts the indicated container',
    command_key=f'restart:{container_name}',
    prompt_func=permission_prompt,
  )


@tool
def download_image(image_name: str) -> str:
  """Downloads a Docker image from a registry"""
  command_preview = build_command_preview(['docker', 'pull', image_name])

  def action():
    client = get_docker_client()
    client.images.pull(image_name)
    return f'Image {image_name} downloaded'

  return permission_manager.execute(
    operation='download_image',
    fn=action,
    fn_kwargs={},
    command_preview=command_preview,
    impact='Downloads a Docker image',
    command_key=f'download:{image_name}',
    prompt_func=permission_prompt,
  )


@tool
def create_container(container_image: str, container_name: str) -> str:
  """Creates and starts a new Docker container with given image and name"""
  images = get_docker_client().images.list()
  if container_image not in [img.tags[0] for img in images]:
    download_image(container_image)

  command_preview = build_command_preview(['docker', 'run', '-d', '--name', container_name, container_image])

  def action():
    client = get_docker_client()
    container = client.containers.create(container_image, name=container_name)
    container.start()
    return f'Container {container_name} created and started'

  return permission_manager.execute(
    operation='create_container',
    fn=action,
    fn_kwargs={},
    command_preview=command_preview,
    impact='Creates and starts a new container',
    command_key=f'create:{container_image}:{container_name}',
    prompt_func=permission_prompt,
  )


@tool
def delete_container(container_name: str) -> str:
  """Stops and removes the specified Docker container"""
  command_preview = build_command_preview(['docker', 'rm', '-f', container_name])

  def action():
    client = get_docker_client()
    container = client.containers.get(container_name)
    container.stop()
    container.remove()
    return f'Container {container_name} deleted'

  return permission_manager.execute(
    operation='delete_container',
    fn=action,
    fn_kwargs={},
    command_preview=command_preview,
    impact='Stops and removes the indicated container',
    command_key=f'delete:{container_name}',
    prompt_func=permission_prompt,
  )


@tool
def stop_container(container_name: str) -> str:
  """Stops the specified Docker container"""
  command_preview = build_command_preview(['docker', 'stop', container_name])

  def action():
    client = get_docker_client()
    container = client.containers.get(container_name)
    container.stop()
    return f'Container {container_name} stopped'

  return permission_manager.execute(
    operation='stop_container',
    fn=action,
    fn_kwargs={},
    command_preview=command_preview,
    impact='Stops the indicated container',
    command_key=f'stop:{container_name}',
    prompt_func=permission_prompt,
  )


def background_monitor_task(container_name: str, threshold: float):
  while True:
    try:
      client = get_docker_client()
      container = client.containers.get(container_name)
      stats = container.stats(stream=False)
      mem_usage = stats['memory_stats']['usage']
      mem_limit = stats['memory_stats']['limit']
      mem_percent = (mem_usage / mem_limit) * 100
      if mem_percent > threshold:
        console.print(
          f'[blink bold red]Warning: Memory usage {mem_percent:.2f}% exceeds threshold {threshold}%[/blink bold red]'
        )
        console.print('[yellow]Autodiagnostic[/yellow]')
        alert_msg = f'Warning: Memory usage {mem_percent:.2f}% exceeds threshold {threshold}%'
        run_agent_flow(alert_msg)
        break
    except Exception:
      pass
    time.sleep(10)


@tool
def start_monitoring(container_name: str, threshold_percent: float) -> str:
  """Starts memory monitoring for the container and alerts if threshold is exceeded"""
  command_preview = build_command_preview(['monitor', 'memory', container_name, f'threshold={threshold_percent}'])

  def action():
    t = threading.Thread(target=background_monitor_task, args=(container_name, threshold_percent), daemon=True)
    t.start()
    return f'Monitoring started for container {container_name} with threshold {threshold_percent}%'

  return permission_manager.execute(
    operation='start_monitoring',
    fn=action,
    fn_kwargs={},
    command_preview=command_preview,
    impact='Starts monitoring that can trigger container restarts',
    command_key=f'monitor:{container_name}:{threshold_percent}',
    prompt_func=permission_prompt,
  )


def sanitize_command(command: str) -> str:
  """Sanitizes the command to prevent common injection attacks."""
  # Deny chaining characters
  if re.search(r'[;&|]', command):
    raise ValueError('Command chaining characters (;, &, |) are not allowed.')

  # Deny command substitution
  if re.search(r'\$\(.*\)|`.*`', command):
    raise ValueError('Command substitution is not allowed.')

  return command


@tool
def exec_command(container_name: str, command: str) -> str:
  """Executes a command in the specified Docker container"""
  try:
    safe_command = sanitize_command(command)
  except ValueError as e:
    return f'Security Error: {e}'

  command_preview = build_command_preview(['docker', 'exec', container_name, safe_command])

  def action():
    client = get_docker_client()
    container = client.containers.get(container_name)
    exec_id = container.exec_run(safe_command)
    return exec_id.output.decode('utf-8').strip()

  return permission_manager.execute(
    operation='exec_command',
    fn=action,
    fn_kwargs={},
    command_preview=command_preview,
    impact='Executes a command in the indicated container',
    command_key=f'exec:{container_name}:{safe_command}',
    prompt_func=permission_prompt,
  )


tools = [
  check_resource,
  get_docker_logs,
  list_containers,
  inspect_container,
  restart_docker_container,
  create_container,
  delete_container,
  stop_container,
  start_monitoring,
  exec_command,
  download_image,
]


if os.getenv('LLM') == 'deepseek':
  from llm.deepseek import llm
else:
  from llm.chatgpt import llm


memory = MemorySaver()
agent_executor = create_react_agent(llm, tools, checkpointer=memory)


def run_agent_flow(user_input: str):
  initial_state = {'messages': [HumanMessage(content=user_input)]}
  for event in agent_executor.stream(initial_state, global_config):
    if 'agent' in event:
      msg = event['agent']['messages'][0]
      if msg.content:
        console.print('\n[bold magenta]Agent[/bold magenta]')
        console.print(Markdown(msg.content))
