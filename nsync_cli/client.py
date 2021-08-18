import base64
import json
import stat
import sys
from pathlib import Path
from string import Template

import click
import httpx
from cryptography.fernet import Fernet
from py_essentials import hashing as hs

from nsync_cli.config import get_config
from nsync_cli.queries.login import login_query
from nsync_cli.queries.user import user_query, key_query, save_key
from nsync_cli.queries.file import save_version_outer, save_version_inner, pull_versions


class Client:
	QUERIES = {
		'login': Template(login_query),
		'user': Template(user_query),
		'key': Template(key_query),
		'save_key': Template(save_key),
		'save_version': [Template(save_version_outer), Template(save_version_inner)],
		'pull_versions': Template(pull_versions),
	}

	def __init__(self, config_dir):
		self.cookie_path = config_dir / 'cookies.json'
		self.config = get_config(config_dir)
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
			self.cookie_path.parent.mkdir()

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

		return user

	def check_key(self, name):
		self.check_auth()

		data = self.graphql('key', key=name)
		if len(data['data']['syncKeys']['edges']):
			self.error(f'Key is already registered: {name}')
			sys.exit(1)

	def register_key(self, name):
		return self.graphql('save_key', key=name)

	@staticmethod
	def shrink_path(p, home):
		try:
			upload_path = p.relative_to(home)

		except ValueError:
			return str(p)

		else:
			return '{{HOME}}/' + str(upload_path)

	@staticmethod
	def expand_path(p, home):
		p = p.replace('{{HOME}}', str(home))
		return Path(p)

	def pull_paths(self, paths, home, confirmed):
		self.check_auth()

		local_paths = {}
		for p in paths:
			local_paths[self.shrink_path(p, home)] = p

		data = self.graphql('pull_versions')
		pulling = {}
		for f in data['data']['syncFiles']['edges']:
			file = f['node']
			version = file['latestVersion']

			if local_paths and file['path'] not in local_paths:
				continue

			if version:
				local_path = self.expand_path(file['path'], home)
				local_perms = None
				local_hash = None
				if local_path.exists():
					local_perms = stat.S_IMODE(local_path.stat().st_mode)
					if not local_path.is_dir():
						local_hash = hs.fileChecksum(local_path, algorithm='sha256')
						local_hash = 'narf'

				if version['permissions'] != local_perms or version['uhash'] != local_hash:
					version['local'] = local_path
					pulling[file['path']] = version

		if pulling:
			self.echo('Pulling Files:')
			for remote, v in pulling.items():
				self.echo(' {}'.format(v['local']))

			if confirmed or click.confirm('Do you want to continue?'):
				print('TODO PULL')

		else:
			self.echo('Nothing to pull')


	def push_paths(self, paths, home, confirmed):
		self.check_auth()

		batch = []
		furry = Fernet(self.config['key']['value'])
		for p in paths:
			upload_path = self.shrink_path(p, home)

			uhash = ''
			file_type = 'file'
			ebody = ''
			permissions = stat.S_IMODE(p.stat().st_mode)
			if p.is_dir():
				file_type = 'dir'

			else:
				uhash = hs.fileChecksum(p, algorithm='sha256')
				# todo: check hash
				with p.open('rb') as fh:
					ebody = furry.encrypt(fh.read())

				ebody = base64.b64encode(ebody).decode()

			b = {
				'key': self.config['key']['name'],
				'path': upload_path,
				'uhash': uhash,
				'permissions': permissions,
				'filetype': file_type,
				'ebody': ebody,
				'original_path': p,
			}
			batch.append(b)

		self.echo('Pushing Files:')
		for b in batch:
			self.echo(' {}'.format(b['original_path']))

		if confirmed or click.confirm('Do you want to continue?'):
			data = self.graphql_batch('save_version', batch)
			self.print('Upload Complete')
			return data
