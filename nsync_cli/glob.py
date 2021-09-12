import os
from pathlib import Path

def glob(path_glob):
	if '*' in path_glob:
		path = Path(path_glob)
		if path.is_absolute():
			parts = path_glob.split(os.sep)
			abs_parts = ['']
			glob_parts = []

			for p in parts:
				if glob_parts or '*' in p:
					glob_parts.append(p)

				else:
					abs_parts.append(p)

			print(os.sep.join(abs_parts))
			path = Path(os.sep.join(abs_parts))
			print(os.sep.join(glob_parts))
			return path.glob(os.sep.join(glob_parts))

		else:
			return Path().glob(path_glob)

	else:
		return [Path(path_glob)]
