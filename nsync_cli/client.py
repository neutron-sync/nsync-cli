import json
import sys
from string import Template

import click
import httpx

from nsync_cli.config import get_config
from nsync_cli.queries.login import login_query
from nsync_cli.queries.user import user_query, key_query, save_key


class Client:
	QUERIES = {
		'login': Template(login_query),
		'user': Template(user_query),
		'key': Template(key_query),
		'save_key': Template(save_key),
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

	def save_cookies(self):
		self.cookies = dict(self.last_response.cookies)

		if not self.cookie_path.parent.exists():
			self.cookie_path.parent.mkdir()

		with self.cookie_path.open('w') as fh:
			fh.write(json.dumps(dict(self.last_response.cookies), indent=2))

	def graphql(self, qname, **params):
		query = self.QUERIES[qname].substitute(**params)
		self.last_response = self.client.post('/graphql', data={'query': query}, cookies=self.cookies)
		data = self.last_response.json()
		self.save_cookies()

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

	def push_paths(self, paths, home):
		self.check_auth()
