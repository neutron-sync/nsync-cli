import os
import shutil
import sys
from pathlib import Path

import pendulum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from py_essentials import hashing as hs
from tabulate import tabulate


class CommandsMixin:
  def add_paths(self, paths, confirmed):
    self.check_auth()

    batch = []
    furry = Fernet(self.config['key']['value'])
    for p in paths:
      ignore = False

      for ext in self.config['extensions_ignore']:
        if ext in p.suffixes:
          ignore = True
          break

      if ignore:
        continue

      batch.append(self.prepare_upload(p, furry))

    if not batch:
      self.echo('Nothing to add')
      return

    self.echo('Pushing Files:')
    for b in batch:
      self.echo(' {}'.format(b['original_path']))

    if confirmed or click.confirm('Do you want to continue?'):
      data = self.graphql_batch('save_version', batch)
      self.print('Upload Complete')
      self.set_last_transaction()
      return data

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

  def delete(self, item_type, item_id, confirmed):
    self.check_auth()

    if confirmed or click.confirm(f'Are you sure you want to delete {item_type}:{item_id}?'):
      data = self.graphql('delete_item', item_type=item_type, item_id=item_id)
      if (data['data']['deleteItem']['success']):
        self.print(f"Deleted Successfully {item_type}:{item_id}")

      else:
        self.error(f"Not Found {item_type}:{item_id}")
        sys.exit(1)

  def diff (self, path, version_id=None):
    self.check_auth()

  def login(self, username, password):
    data = self.graphql('login', username=username, password=password)
    if data['data']['login']['user']:
      self.print('Login Successful')

    else:
      self.error('Login Failed')
      sys.exit(1)

  def pull_paths(self, paths, force=False, confirmed=False):
    self.check_auth()
    furry = Fernet(self.config['key']['value'])

    pulling, remote_last = self.pull_data(paths, force)
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

        self.set_last_transaction()

    else:
      self.echo('Nothing to pull')
      self.set_last_transaction()

  def push(self, confirmed=False):
    self.check_auth()
    self.check_transaction()
    furry = Fernet(self.config['key']['value'])

    data = self.pull_with_pagination(self.config['key']['name'])
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

          if local_hash == version['uhash']:
            if local_perms != version['permissions']:
              version['reason'] = 'Permissions diff'
              version['local'] = local_path
              pushing[file['path']] = version

          else:
            remote_ts = pendulum.parse(version['timestamp'])
            if local_modified > remote_ts:
              version['reason'] = 'modifed after remote'

            elif local_modified < remote_ts:
              version['reason'] = 'older than remote'

            else:
              version['reason'] = 'out of sync'

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
        self.set_last_transaction()
        return data

    else:
      self.echo('Nothing to push')

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

  def status(self, show_all=False):
    self.check_auth()
    local_last, remote_last = self.get_last_transaction()
    self.echo(f'Last Transactions\n  Local: {local_last}    Remote: {remote_last}\n')

    headers = ['File', 'Vers', 'Dir', 'Path', 'Trans', 'Timestamp UTC', 'Local Status']
    table = []
    pulling, remote_last = self.pull_data([], always_reason=True)
    for remote, v in pulling.items():
      dt = pendulum.parse(v['timestamp']).to_rfc1123_string()[:-6]

      if show_all or v['reason'] != 'in sync':
        if v['isDir']:
          table.append([v['fileId'], v['rawId'], 'd', v['local'], v['transaction']['rawId'], dt, v['reason']])

        else:
          table.append([v['fileId'], v['rawId'], '', v['local'], v['transaction']['rawId'], dt, v['reason']])

    if table:
      self.echo(f'List files for key: {self.config["key"]["name"]}')
      self.echo(tabulate(table, headers))

    else:
      self.print('Everything in Sync')

    self.set_last_transaction()

  def view_version(self, version_id, show=False):
    self.check_auth()
    data = self.graphql('view_version', version_id=version_id)

    if data['data']['fileVersions']['edges']:
      version = data['data']['fileVersions']['edges'][0]['node']

      if version['isDir']:
        self.echo(f"Directory: {version['syncFile']['path']}")

      else:
        self.echo(f"File: {version['syncFile']['path']}")

      self.echo(f"Version: {version['rawId']}")
      self.echo(f"Permissions: {version['linuxPerm']}")
      self.echo(f"Timestamp: {version['timestamp']}")

      if version['isDir']:
        return

      if show:
        response = httpx.get(version['download'])
        self.echo('\nEncrypted Text:')
        ebody = base64.b64decode(response.content)
        self.echo(ebody.decode())

        self.echo('\nUnencrypted Text:')
        furry = Fernet(self.config['key']['value'])
        body = furry.decrypt(ebody)
        self.echo(body.decode())

    else:
      self.error(f'Not found version:{version_id}')
      sys.exit(1)

