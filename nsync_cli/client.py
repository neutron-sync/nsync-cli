import base64
import json
import stat
import sys
from string import Template

import click
import httpx
from cryptography.fernet import Fernet
from py_essentials import hashing as hs

from nsync_cli.config import get_config
from nsync_cli.queries.login import login_query
from nsync_cli.queries.user import user_query, key_query, save_key
from nsync_cli.queries.file import save_version_outer, save_version_inner


class Client:
	QUERIES = {
		'login': Template(login_query),
		'user': Template(user_query),
		'key': Template(key_query),
		'save_key': Template(save_key),
		'save_version': [Template(save_version_outer), Template(save_version_inner)]
	}

	def __init__(self, config_dir):
		self.cookie_path = config_dir / 'cookies.json'
		self.config = get_config(config_dir)
		self.cookies = {}

		if self.cookie_path.exists():
			with self.cookie_path.open('r') as fh:
				self.cookies = json.loads(fh.read())

		self.client = httpx.Client(cookies=self.cookies, base_url=self.config['server'])

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

		if 'errors' in data and len(data['errors']):
			for e in data['errors']:
				self.error(e['message'])

			sys.exit(1)

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

	def push_paths(self, paths, home, confirmed):
		self.check_auth()

		batch = []
		furry = Fernet(self.config['key']['value'])
		for p in paths:
			try:
				upload_path = p.relative_to(home)

			except ValueError:
				upload_path = str(p)

			else:
				upload_path = '{{HOME}}/' + str(upload_path)

			uhash = None
			is_dir = p.is_dir()
			ebody = None
			permissions = stat.S_IMODE(p.stat().st_mode)
			if not is_dir:
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
				'is_dir': is_dir,
				'ebody': ebody,
				'original_path': p,
			}
			batch.append(b)

		self.echo('Pushing Files:')
		for b in batch:
			self.echo(' {}'.format(b['original_path']))

		if confirmed or click.confirm('Do you want to continue?'):
			self.graphql_batch('save_version', batch)
			self.print('Upload Complete')
