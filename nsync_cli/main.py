#!/usr/bin/env python3

import glob
import os
import sys

from typing import List
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
def push(
	path_glob: List[str],
	config_dir: Path = config_dir_opt,
	confirmed: bool = typer.Option(False, "--confirmed", help="Continue skipping cofirmations"),
):
	paths = []
	for g in path_glob:
		found = glob.glob(g, recursive=True)
		for p in found:
			p = Path(os.path.abspath(p))
			if p.is_symlink():
				pass

			else:
				paths.append(p)

	if not paths:
		echo('Nothing to push')
		sys.exit(0)

	echo('The following paths will be pushed')
	for p in paths:
		echo(f'  {p}')

	if confirmed or click.confirm('Do you want to continue?'):
		client = Client(config_dir)
		client.push_paths(paths, str(HOME))

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
	secho(f'Wrote: {key_path}')

	config = get_config(config_dir)
	config['key'] = {'name': key_name, 'path': str(key_path)}
	save_config(config_dir, config)

	client.register_key(key_name)
	secho(f'Key Registered: {key_name}')


def error(msg, exit=False):
	click.secho('Error: ' + msg, fg='red', err=True)

	if exit:
		sys.exit(1)


def echo(msg):
	click.secho(msg)


def secho(msg):
	click.secho(msg, fg='green')


if __name__ == "__main__":
	app()
