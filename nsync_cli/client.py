import json
from string import Template

import click
import httpx

from nsync_cli.config import get_config
from nsync_cli.queries.login import query as login_query


class Client:
	QUERIES = {
		'login': Template(login_query)
	}

	def __init__(self, config_dir):
		cookie_path = config_dir / 'cookies.json'
		self.config = get_config(config_dir)
		self.cookies = {}

		if cookie_path.exists():
			with cookie_path.open('r') as fh:
				self.cookies = json.loads(fh.read())

		self.client = httpx.Client(cookies=self.cookies, base_url=self.config['server'])

	def graphql(self, qname, **params):
		query = self.QUERIES[qname].substitute(**params)
		self.last_response = self.client.post('/graphql', data={'query': query})
		return self.last_response.json()

	def login(self):
		username = click.prompt('Username')
		password = click.prompt('Password', hide_input=True)
		return self.graphql('login', username=username, password=password)
