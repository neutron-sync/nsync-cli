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
	fileType: $filetype
	ebody: $ebody
}) {
  transaction
  errors{
    messages
  }
}
"""

pull_versions = """
query{
  syncFiles(first:500) {
    edges{
      node{
        path
        latestVersion{
          download
          permissions
          uhash
          isDir
        }
      }
    }
  }
}
"""

list_versions = """
query{
  syncFiles(first:500) {
    edges{
      node{
        path
        latestVersion{
          isDir
          created
          transaction{
            id
          }
        }
      }
    }
  }
}
"""
