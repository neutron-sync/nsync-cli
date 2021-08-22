import json
import os

DEFAULT_SERVER_URL = 'https://www.neutronsync.com'


def get_config(config_dir):
  config_path = config_dir / 'config.json'
  if config_path.exists():
    with config_path.open('r') as fh:
      return json.loads(fh.read())

  return {
    'server_url': DEFAULT_SERVER_URL,
    'expansions': {'HOME': os.environ['HOME']},
    'backups': True,
    'backup_suffix': '.backup',
    'extensions_ignore': ['.backup'],
  }


def save_config(config_dir, config):
  config_path = config_dir / 'config.json'
  with config_path.open('w') as fh:
    fh.write(json.dumps(config, indent=2))

  config_path.chmod(0o600)
