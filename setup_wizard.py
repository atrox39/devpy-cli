import os
import stat
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

console = Console()


def run_setup(force=False):
  """
  Runs the interactive setup wizard for .env configuration.
  If .env exists and force is False, it returns immediately.
  """
  env_file = '.env'
  if os.path.exists(env_file) and not force:
    return

  console.print(Panel.fit('[bold cyan]Welcome to DevPy CLI Setup[/bold cyan]', border_style='cyan'))
  console.print("\n[yellow]It seems like you haven't configured the application yet.[/yellow]")
  console.print("Let's set up your environment variables to get started.\n")

  # Select LLM Provider
  console.print('[bold]Step 1: Select your LLM Provider[/bold]')
  providers = ['DeepSeek', 'OpenAI', 'Anthropic', 'Google', 'Other']
  provider = Prompt.ask('Choose a provider', choices=providers, default='DeepSeek')

  api_key_var = ''
  llm_value = ''

  if provider == 'DeepSeek':
    api_key_var = 'DEEPSEEK_API_KEY'
    llm_value = 'deepseek'
  elif provider == 'OpenAI':
    api_key_var = 'OPENAI_API_KEY'
    llm_value = 'chatgpt'  # Based on existing backend logic
  elif provider == 'Anthropic':
    api_key_var = 'ANTHROPIC_API_KEY'
    llm_value = 'anthropic'
  elif provider == 'Google':
    api_key_var = 'GOOGLE_API_KEY'
    llm_value = 'google'
  else:
    # Custom/Other
    llm_value = Prompt.ask('Enter the LLM identifier (e.g., custom_llm)')
    api_key_var = Prompt.ask('Enter the environment variable name for API Key (e.g., CUSTOM_API_KEY)')

  # Get API Key
  console.print(f'\n[bold]Step 2: Enter your API Key for {provider}[/bold]')
  while True:
    api_key = Prompt.ask(f'Enter value for {api_key_var}', password=True)
    if api_key.strip():
      break
    console.print('[red]API Key cannot be empty. Please try again.[/red]')

  # Create .env content
  env_content = f'LLM={llm_value}\n{api_key_var}={api_key}\n'

  # Optional: Base URL for compatible providers
  if provider in ['DeepSeek', 'Other']:
    if provider == 'DeepSeek':
      default_url = 'https://api.deepseek.com/v1'
    else:
      default_url = ''

    use_custom_url = Prompt.ask('Do you want to set a custom Base URL?', choices=['y', 'n'], default='n')
    if use_custom_url == 'y':
      base_url = Prompt.ask('Enter Base URL', default=default_url)
      env_content += f'LLM_BASE_URL={base_url}\n'

  # Write to .env
  try:
    with open(env_file, 'w', encoding='utf-8') as f:
      f.write(env_content)

    # Harden file permissions (read/write only for owner)
    os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)

    console.print(f'\n[green]Successfully created {env_file}![/green]')
    console.print("[dim]You can reconfigure this later using 'config llm' command.[/dim]\n")
  except Exception as e:
    console.print(f'\n[bold red]Error writing .env file: {e}[/bold red]')
    exit(1)

  console.print(Panel.fit('[bold green]Setup Complete! Launching CLI...[/bold green]', border_style='green'))


if __name__ == '__main__':
  run_setup(force=True)
