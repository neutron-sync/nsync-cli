#!/usr/bin/env python3

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
from nsync_cli.globber import get_paths

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
  envvar="NSYNC_CONFIG_DIR"
)


@app.command()
def status(
  all: bool = typer.Option(False, "--all", help="Display all file states, even in sync."),
  config_dir: Path = config_dir_opt,
):
  client = Client(config_dir)
  client.status(all)


@app.command()
def push(
    config_dir: Path = config_dir_opt,
    confirmed: bool = typer.Option(False, "--confirmed", help="Continue skipping confirmations"),
):
  client = Client(config_dir)
  data = client.push(confirmed)


@app.command()
def pull(
    path_glob: List[str] = typer.Argument(None),
    config_dir: Path = config_dir_opt,
    force: bool = typer.Option(False, "--force", help="Force all files to down"),
    confirmed: bool = typer.Option(False, "--confirmed", help="Continue skipping confirmations"),
):
  paths = []
  for g in path_glob:
    found = get_paths(g)
    for p in found:
      if p.is_symlink():
        pass

      else:
        paths.append(p)

  client = Client(config_dir)
  data = client.pull_paths(paths, force, confirmed)


@app.command()
def add(
    path_glob: List[str],
    config_dir: Path = config_dir_opt,
    confirmed: bool = typer.Option(False, "--confirmed", help="Continue skipping confirmations"),
):
  paths = []
  for g in path_glob:
    found = get_paths(g)
    for p in found:
      if p.is_symlink():
        pass

      else:
        paths.append(p)

  if not paths:
    echo('Nothing to add')
    sys.exit(0)

  client = Client(config_dir)
  data = client.add_paths(paths, confirmed)
  if data and 'data' in data:
    for key, value in data['data'].items():
      secho('Transaction Saved: {}'.format(value['transaction']))
      return


@app.command()
def delete(
    item_type: str,
    item_id: str,
    config_dir: Path = config_dir_opt,
    confirmed: bool = typer.Option(False, "--confirmed", help="Continue skipping confirmations"),
):
  client = Client(config_dir)
  client.delete(item_type, item_id, confirmed)


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
  secho('!!! Don\'t Lose Your Config File and Key: {}'.format(config_dir / 'config.json'))

  client.register_key(key_name)
  secho(f'Key Registered as: {key_name}')


@app.command()
def start_key_exchange(
  expassword: str = typer.Option(None, prompt='Temporary Password for Exchange Encryption', hide_input=True),
  config_dir: Path = config_dir_opt
):
  client = Client(config_dir)
  client.start_exchange(expassword)


@app.command()
def complete_key_exchange(
  expassword: str = typer.Option(None, prompt='Temporary Exchange Password', hide_input=True),
  exphrase: str = typer.Option(None, prompt='Exchange Phrase'),
  config_dir: Path = config_dir_opt
):
  client = Client(config_dir)
  client.complete_exchange(expassword, exphrase)


@app.command()
def view_version(version_id: int, config_dir: Path = config_dir_opt):
  client = Client(config_dir)
  client.view_version(version_id)


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
