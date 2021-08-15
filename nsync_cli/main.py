#!/usr/bin/env python3

import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet
import click
import httpx
import typer

from nsync_cli.config import get_config, save_config
from nsync_cli.client import Client

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


@app.command()
def start(config_dir: Path = config_dir_opt):
	error('Not Implemented', exit=True)


@app.command()
def stop():
	error('Not Implement', exit=True)


@app.command()
def push():
	pass
	# stat.S_IMODE(st.st_mode)


@app.command()
def login(
		username: str = typer.Option(None, prompt=True),
		password: str = typer.Option(None, prompt=True, hide_input=True),
		config_dir: Path = config_dir_opt,
	):
		client = Client(config_dir)
		client.login(username, password)


@app.command()
def keygen(
	key_name: str = typer.Argument('default'),
	key_path: Path = key_path_arg,
	config_dir: Path = config_dir_opt,
):
	client = Client(config_dir)
	client.check_key(key_name)

	key = Fernet.generate_key().decode()

	if not key_path.parent.exists():
		os.makedirs(str(key_path.parent))

	if key_path.exists():
		error(f'Key file already exists: {key_path}')
		sys.exit(1)

	with key_path.open('w') as fh:
		fh.write(key)

	key_path.chmod(0o600)
	echo(f'Wrote: {key_path}')

	config = get_config(config_dir)
	config['key'] = {'name': key_name, 'path': str(key_path)}
	save_config(config_dir, config)

	client.register_key(key_name)
	echo(f'Key Registered: {key_name}')


def error(msg, exit=False):
	click.secho('Error: ' + msg, fg='red', err=True)

	if exit:
		sys.exit(1)


def echo(msg):
	click.secho(msg, fg='green')


if __name__ == "__main__":
	app()
