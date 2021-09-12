import os
import glob

from pathlib import Path

def get_paths(path_glob):
	paths = glob.glob(path_glob, recursive=True)
	ret = []
	for p in paths:
		p = Path(p)
		if not p.is_absolute():
			p = p.resolve()

		ret.append(p)

	return ret
