user_query = """
query {
  users(first:1) {
    edges{
      node{
        username
        id
      }
    }
  }
}
"""

key_query = """
query {
  syncKeys(first: 1, name: $key) {
    edges{
      node{
        name
        id
      }
    }
  }
}
"""

save_key = """
mutation {
  addKey(input: {name: $key}) {
    syncKey{
      name
      id
    }
    errors{
      messages
    }
  }
}
"""
