start_exchange = """
mutation {
  startKeyExchange(
    input: {
      key: $key
      salt: $salt
      etext: $etext
    }
  ) {
    phrase
    errors{
      messages
    }
  }
}
"""

complete_exchange = """
mutation {
  completeKeyExchange(
    input: {
      phrase: $phrase
    }
  ) {
    key
    salt
    etext
    errors{
      messages
    }
  }
}
"""
