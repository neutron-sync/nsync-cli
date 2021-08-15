#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet
import typer

app = typer.Typer()

HOME = Path(os.environ['HOME'])
CONFIG_DIR = HOME / '.config' / 'nsync'

config_dir_opt = typer.Option(
  CONFIG_DIR,
	exists=False,
	file_okay=False,
	dir_okay=True,
	writable=True,
	readable=True,
	resolve_path=True,
)

key_path_arg = typer.Argument(
	CONFIG_DIR / 'key.txt',
	exists=False,
	file_okay=True,
	dir_okay=False,
	writable=True,
	readable=True,
	resolve_path=True,
)


def get_config(config_dir):
	config_path = config_dir / 'config.json'
	if config_path.exists():
		with config_path.open('r') as fh:
			return json.loads(fh.read())

	return {'endpoint': 'http://localhost:8000/graphql'}


def save_config(config_dir, config):
	config_path = config_dir / 'config.json'
	with config_path.open('w') as fh:
		fh.write(json.dumps(config, indent=2))


@app.command()
def start(config_dir: Path = config_dir_opt):
	pass


@app.command()
def stop():
	pass


@app.command()
def keygen(
	key_name: str = typer.Argument('default'),
	key_path: Path = key_path_arg,
	config_dir: Path = config_dir_opt,
):
	key = Fernet.generate_key().decode()

	if not key_path.parent.exists():
		os.makedirs(str(key_path.parent))

	if key_path.exists():
		sys.stderr.write(f'Key file already exists: {key_path}\n')
		sys.exit(1)

	with key_path.open('w') as fh:
		fh.write(key)

	key_path.chmod(0o600)
	print('Wrote:', key_path)

	config = get_config(config_dir)
	config['key'] = {'name': key_name, 'path': str(key_path)}
	save_config(config_dir, config)


if __name__ == "__main__":
	app()
