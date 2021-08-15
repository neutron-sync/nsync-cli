import json


def get_config(config_dir):
	config_path = config_dir / 'config.json'
	if config_path.exists():
		with config_path.open('r') as fh:
			return json.loads(fh.read())

	return {'server': 'http://localhost:8000'}


def save_config(config_dir, config):
	config_path = config_dir / 'config.json'
	with config_path.open('w') as fh:
		fh.write(json.dumps(config, indent=2))
