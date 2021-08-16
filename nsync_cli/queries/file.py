save_version_outer = """
mutation {
  $batch
}
"""

save_version_inner = """
$qname: saveVersion(input: {
	key: $key
	path: $path
	uhash: $uhash
	permissions: $permissions
	isDir: $is_dir
	ebody: $ebody
}) {
  transaction
  errors{
    messages
  }
}
"""
