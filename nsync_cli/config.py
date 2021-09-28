import json
import os

DEFAULT_SERVER_URL = 'https://www.neutronsync.com'


def set_defaults(data):
  if 'last_transction' not in data:
    data['last_transction'] = None

  if 'expansions' not in data:
    data['expansions'] = {'HOME': os.environ['HOME']}

  if 'backups' not in data:
    data['backups'] = True

  if 'backup_suffix' not in data:
    data['backup_suffix'] = '.backup'

  if 'extensions_ignore' not in data:
    data['extensions_ignore'] = ['.backup']

  return data


def get_config(config_dir):
  config_path = config_dir / 'config.json'
  if config_path.exists():
    with config_path.open('r') as fh:
      data = json.loads(fh.read())
      data = set_defaults(data)
      return data

  return {
    'server_url': DEFAULT_SERVER_URL,
    'expansions': {'HOME': os.environ['HOME']},
    'backups': True,
    'backup_suffix': '.backup',
    'extensions_ignore': ['.backup'],
    'last_transction': None,
  }


def save_config(config_dir, config):
  config_path = config_dir / 'config.json'
  with config_path.open('w') as fh:
    fh.write(json.dumps(config, indent=2))

  config_path.chmod(0o600)
  config_dir.chmod(0o700)
