user_query = """
query {
  users(first:1) {
    edges{
      node{
        username
        id
        hasCredit
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

last_transaction = """
query {
  fileTransactions (first: 1) {
    edges{
      node {
        id
        intId
      }
    }
  }
}
"""
