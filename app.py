import os

# Check for .env before importing frontend_cli which imports backend
if not os.path.exists('.env'):
  try:
    from setup_wizard import run_setup

    run_setup()
  except ImportError:
    print('Error: setup_wizard module not found. Please ensure all files are installed correctly.')
    exit(1)

from frontend_cli import run_cli


if __name__ == '__main__':
  run_cli()
