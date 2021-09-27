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
  timestamp: $timestamp
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
  fileTransactions (first: 1) {
    edges{
      node {
        id
        intId
      }
    }
  }
  syncFiles(first:50, key: $key) {
    edges{
      node{
        path
        latestVersion{
          download
          permissions
          timestamp
          uhash
          isDir
          created
          transaction {
            id
            intId
          }
        }
      }
    }
    pageInfo{
      startCursor
      endCursor
      hasNextPage
    }
  }
}
"""

pull_versions_page = """
query{
  syncFiles(first:50, key: $key, after: $after) {
    edges{
      node{
        path
        latestVersion{
          download
          permissions
          timestamp
          uhash
          isDir
          created
          transaction {
            id
            intId
          }
        }
      }
    }
    pageInfo{
      startCursor
      endCursor
      hasNextPage
    }
  }
}
"""
