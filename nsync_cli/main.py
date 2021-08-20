#!/usr/bin/env python3

import glob
import os
import sys

from typing import List, Optional
from pathlib import Path

from cryptography.fernet import Fernet
import click
import httpx
import typer

import nsync_cli
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
def list_server_files(config_dir: Path = config_dir_opt):
  client = Client(config_dir)
  client.list_server()


@app.command()
def pull(
    path_glob: List[str] = typer.Argument(None),
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

  client = Client(config_dir)
  data = client.pull_paths(paths, confirmed)


@app.command()
def add(
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
    echo('Nothing to add')
    sys.exit(0)

  client = Client(config_dir)
  data = client.push_paths(paths, confirmed)
  if data and 'data' in data:
    for key, value in data['data'].items():
      secho('Transaction Saved: {}'.format(value['transaction']))
      return


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
    config_dir: Path = config_dir_opt,
):
  client = Client(config_dir)
  client.check_key(key_name)

  key = Fernet.generate_key().decode()
  config = get_config(config_dir)
  if 'key' in config and 'value' in config['key']:
    error('Key already exists: {} {}'.format(config['key']['name'], config['key']['value']))
    sys.exit(1)

  config['key'] = {'name': key_name, 'value': key}
  save_config(config_dir, config)
  secho(f'Saved Key: {key}')
  secho('!!! Don\'t Lose Your Config File and Key: {}'.format(config_dir / 'config.json'))

  client.register_key(key_name)
  secho(f'Key Registered as: {key_name}')


@app.command()
def version():
  secho(f'Version: {nsync_cli.__version__}')

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
