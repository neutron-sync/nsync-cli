login_query = """
mutation {
  login(
    input: {
      username: $username
      password: $password
    }
  ) {
    user{
      username
      sessionExpiration
    }
    errors{
      messages
    }
  }
}
"""
