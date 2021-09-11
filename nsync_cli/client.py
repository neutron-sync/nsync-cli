import base64
import datetime
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from string import Template

import click
import httpx
import pendulum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from py_essentials import hashing as hs
from tabulate import tabulate

from nsync_cli.config import get_config, save_config
from nsync_cli.queries.login import login_query
from nsync_cli.queries.user import user_query, key_query, save_key
from nsync_cli.queries.file import save_version_outer, save_version_inner, pull_versions, list_versions
from nsync_cli.queries.exchange import start_exchange, complete_exchange

class Client:
  QUERIES = {
    'login': Template(login_query),
    'user': Template(user_query),
    'key': Template(key_query),
    'save_key': Template(save_key),
    'save_version': [Template(save_version_outer), Template(save_version_inner)],
    'pull_versions': Template(pull_versions),
    'list_versions': Template(list_versions),
    'start_exchange': Template(start_exchange),
    'complete_exchange': Template(complete_exchange),
  }

  def __init__(self, config_dir):
    self.cookie_path = config_dir / 'cookies.json'
    self.config = get_config(config_dir)
    self.config_dir = config_dir
    self.cookies = {}

    if self.cookie_path.exists():
      with self.cookie_path.open('r') as fh:
        self.cookies = json.loads(fh.read())

    self.client = httpx.Client(cookies=self.cookies, base_url=self.config['server_url'])

  @staticmethod
  def error(msg):
    click.secho('Error: ' + msg, fg='red', err=True)

  @staticmethod
  def print(msg):
    click.secho(msg, fg='green')

  @staticmethod
  def echo(msg):
    click.secho(msg)

  def save_cookies(self):
    self.cookies = dict(self.last_response.cookies)

    if not self.cookie_path.parent.exists():
      self.cookie_path.parent.mkdir(parents=True)

    with self.cookie_path.open('w') as fh:
      fh.write(json.dumps(dict(self.last_response.cookies), indent=2))

    self.cookie_path.chmod(0o600)

  @staticmethod
  def set_types(params):
    for key, value in params.items():
      if isinstance(value, str):
        params[key] = f'"{value}"'

      elif isinstance(value, bool):
        if value:
          params[key] = 'true'

        else:
          params[key] = 'false'

      elif value is None:
        params[key] = 'null'

  def graphql(self, qname, **params):
    self.set_types(params)
    query = self.QUERIES[qname].substitute(**params)
    data = self.make_query(query)

    if 'errors' in data and len(data['errors']):
      for e in data['errors']:
        self.error(e['message'])

      sys.exit(1)

    return data

  def make_query(self, query):
    self.last_response = self.client.post('/graphql', data={'query': query}, cookies=self.cookies)
    data = self.last_response.json()
    self.save_cookies()
    return data

  def graphql_batch(self, qname, batch):
    outer, inner = self.QUERIES[qname]
    queries = ''

    for i, b in enumerate(batch):
      self.set_types(b)
      qname = f'query{i}'
      queries += inner.substitute(qname=qname, **b) + '\n'

    query = outer.substitute(batch=queries)
    data = self.make_query(query)

    if data and 'errors' in data and len(data['errors']):
      for e in data['errors']:
        self.error(e['message'])

    if data and 'data' in data:
      for key, value in data['data'].items():
        if value and 'errors' in value:
          for e in value['errors']:
            self.error(e['message'])

    return data

  def login(self, username, password):
    self.graphql('login', username=username, password=password)
    self.print('Login Successful')

  def check_auth(self):
    data = self.graphql('user')
    try:
      user = data['data']['users']['edges'][0]['node']['username']

    except:
      self.error('Login required')
      sys.exit(1)

    if not data['data']['users']['edges'][0]['node']['hasCredit']:
      self.error('Your credit has expired. Please subscribe to continue.')
      self.error('Go to: {}'.format(self.config['server_url']))
      sys.exit(1)

    return user

  def check_key(self, name):
    self.check_auth()

    data = self.graphql('key', key=name)
    if len(data['data']['syncKeys']['edges']):
      self.error(f'Key is already registered: {name}')
      sys.exit(1)

  def register_key(self, name):
    return self.graphql('save_key', key=name)

  def shrink_path(self, p):
    for key, d in self.config['expansions'].items():
      dpath = Path(d)
      try:
        upload_path = p.relative_to(dpath)

      except ValueError:
        pass

      else:
        return '{{' + key + '}}/' + str(upload_path)

    return str(p)

  def expand_path(self, p):
    for key, d in self.config['expansions'].items():
      if p.startswith('{{' + key + '}}'):
        p = p.replace('{{' + key + '}}', d)

    return Path(p)

  def list_server(self):
    self.check_auth()
    data = self.graphql('list_versions', key=self.config["key"]["name"])
    self.echo(f'List files for key: {self.config["key"]["name"]}')
    table = [['Dir', 'Path', 'Trans', 'Timestamp UTC']]
    for f in data['data']['syncFiles']['edges']:
      file = f['node']
      version = file['latestVersion']

      if version:
        local_path = self.expand_path(file['path'])
        dt = pendulum.parse(version['created']).to_rfc1123_string()[:-6]
        t = base64.b64decode(version['transaction']['id'].encode()).decode().split(':')[-1]
        if version['isDir']:
          table.append(['d', local_path, t, dt])

        else:
          table.append(['', local_path, t, dt])

    self.echo(tabulate(table))

  def push(self, confirmed=False):
    self.check_auth()
    furry = Fernet(self.config['key']['value'])

    data = self.graphql('pull_versions', key=self.config['key']['name'])
    pushing = {}
    missing = {}
    for f in data['data']['syncFiles']['edges']:
      file = f['node']
      version = file['latestVersion']

      if version:
        local_path = self.expand_path(file['path'])
        local_perms = None
        local_hash = None
        local_modified = None

        if local_path.exists():
          fstats = local_path.stat()
          local_perms = stat.S_IMODE(fstats.st_mode)
          local_modified = datetime.datetime.fromtimestamp(fstats.st_mtime, tz=datetime.timezone.utc)
          if not local_path.is_dir():
            local_hash = hs.fileChecksum(local_path, algorithm='sha256')

          if version['uhash'] != local_hash:
            remote_ts = pendulum.parse(version['timestamp'])
            if local_modified > remote_ts:
              version['reason'] = 'modifed after remote'

            elif local_modified < remote_ts:
              version['reason'] = 'older than remote'

            else:
              version['reason'] = 'contents out of sync'

            version['local'] = local_path
            pushing[file['path']] = version

          elif version['permissions'] != local_perms:
            version['reason'] = 'Permissions inconsistent'
            version['local'] = local_path
            pushing[file['path']] = version

        else:
          version['local'] = local_path
          missing[file['path']] = version

    if missing:
      self.echo('Files Missing Locally:')
      for remote, v in missing.items():
        self.echo(f" {v['local']}")

      self.echo("")

    if pushing:
      self.echo('Pushing Files:')
      table = []
      for remote, v in pushing.items():
        table.append([v['local'], v['reason']])

      self.echo(tabulate(table))

      if confirmed or click.confirm('Do you want to continue?'):
        batch = []
        for remote, v in pushing.items():
          batch.append(self.prepare_upload(v['local'], furry))

        data = self.graphql_batch('save_version', batch)
        self.print('Upload Complete')
        return data

    else:
      self.echo('Nothing to push')


  def pull_paths(self, paths, force=False, confirmed=False):
    self.check_auth()
    furry = Fernet(self.config['key']['value'])

    local_paths = {}
    for p in paths:
      local_paths[self.shrink_path(p)] = p

    data = self.graphql('pull_versions', key=self.config['key']['name'])
    pulling = {}
    for f in data['data']['syncFiles']['edges']:
      file = f['node']
      version = file['latestVersion']

      if local_paths and file['path'] not in local_paths:
        continue

      if version:
        local_path = self.expand_path(file['path'])
        local_perms = None
        local_hash = None
        local_modified = None
        if local_path.exists():
          fstats = local_path.stat()
          local_perms = stat.S_IMODE(fstats.st_mode)
          local_modified = datetime.datetime.fromtimestamp(fstats.st_mtime, tz=datetime.timezone.utc)
          if not local_path.is_dir():
            local_hash = hs.fileChecksum(local_path, algorithm='sha256')

        if version['uhash'] != local_hash or force:
          remote_ts = pendulum.parse(version['timestamp'])
          if local_modified is None:
            version['reason'] = 'Does not exist'

          elif local_modified > remote_ts:
            version['reason'] = 'modifed after remote'

          elif local_modified < remote_ts:
            version['reason'] = 'older than remote'

          else:
            if force:
              version['reason'] = 'forced sync'

            else:
              version['reason'] = 'contents out of sync'

          version['local'] = local_path
          pulling[file['path']] = version

        elif version['permissions'] != local_perms:
          version['reason'] = 'Permissions inconsistent'
          version['local'] = local_path
          pulling[file['path']] = version

    if pulling:
      self.echo('Pulling Files:')
      table = []
      for remote, v in pulling.items():
        table.append([v['local'], v['reason']])

      self.echo(tabulate(table))

      if confirmed or click.confirm('Do you want to continue?'):
        for remote, v in pulling.items():
          if not v['local'].parent.exists():
            v['local'].parent.mkdir(parents=True)

          if v['isDir']:
            if not v['local'].exists():
              v['local'].mkdir(parents=True)

          else:
            response = httpx.get(v['download'])
            ebody = base64.b64decode(response.content)
            body = furry.decrypt(ebody)

            if self.config['backups'] and v['local'].exists():
              backup = Path(str(v['local']))
              backup = backup.with_suffix(self.config['backup_suffix'])
              backup.touch()
              shutil.copy2(v['local'], backup)

            with v['local'].open('wb') as fh:
              fh.write(body)

          v['local'].chmod(v['permissions'])
          ts = pendulum.parse(v['timestamp']).timestamp()
          os.utime(v['local'], (ts, ts))

    else:
      self.echo('Nothing to pull')

  def prepare_upload(self, p, furry):
    upload_path = self.shrink_path(p)
    uhash = ''
    file_type = 'file'
    ebody = ''
    fstats = p.stat()
    permissions = stat.S_IMODE(fstats.st_mode)
    timestamp = datetime.datetime.fromtimestamp(fstats.st_mtime, tz=datetime.timezone.utc).isoformat()
    if p.is_dir():
      file_type = 'dir'

    else:
      uhash = hs.fileChecksum(p, algorithm='sha256')
      # todo: check hash
      with p.open('rb') as fh:
        ebody = furry.encrypt(fh.read())

      ebody = base64.b64encode(ebody).decode()

    return {
      'key': self.config['key']['name'],
      'path': upload_path,
      'uhash': uhash,
      'permissions': permissions,
      'timestamp': timestamp,
      'filetype': file_type,
      'ebody': ebody,
      'original_path': p,
    }

  def add_paths(self, paths, confirmed):
    self.check_auth()

    batch = []
    furry = Fernet(self.config['key']['value'])
    ignore = False
    for p in paths:
      for ext in self.config['extensions_ignore']:
        if ext in p.suffixes:
          ignore = True
          break

      if ignore:
        continue

      batch.append(self.prepare_upload(p, furry))

    if not batch:
      self.echo('Nothing to push')
      return

    self.echo('Pushing Files:')
    for b in batch:
      self.echo(' {}'.format(b['original_path']))

    if confirmed or click.confirm('Do you want to continue?'):
      data = self.graphql_batch('save_version', batch)
      self.print('Upload Complete')
      return data

  def start_exchange(self, expassword):
    self.check_auth()

    salt = os.urandom(16)
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    key_for_encryption = base64.urlsafe_b64encode(kdf.derive(expassword.encode())).decode()
    furry = Fernet(key_for_encryption)

    key = self.config['key']['name']
    salt = base64.b64encode(salt).decode()
    etext = furry.encrypt(self.config['key']['value'].encode())
    etext = base64.b64encode(etext).decode()

    data = self.graphql('start_exchange', key=key, salt=salt, etext=etext)
    self.echo('***Exchange Initialized. Note phrase below expires in 15 minutes.***')
    self.print('Exchange Phrase: {}'.format(data['data']['startKeyExchange']['phrase']))

  def complete_exchange(self, expassword, phrase):
    self.check_auth()

    data = self.graphql('complete_exchange', phrase=phrase)['data']['completeKeyExchange']
    if data['salt'] and data['key'] and data['etext']:
      salt = base64.b64decode(data['salt'])
      etext = base64.b64decode(data['etext'])
      key_name = data['key']

      kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
      key_for_encryption = base64.urlsafe_b64encode(kdf.derive(expassword.encode())).decode()
      furry = Fernet(key_for_encryption)

      try:
        key_value = furry.decrypt(etext).decode()

      except:
        self.error('Invalid encryption password.')
        sys.exit(1)

      self.config['key'] = {
        'name': key_name,
        'value': key_value,
      }
      save_config(self.config_dir, self.config)
      self.print('Key exchange successful!')

    else:
      self.error('Unknown phrase or phrase expired')
      sys.exit(1)
