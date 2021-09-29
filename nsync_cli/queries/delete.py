delete_item = """
mutation{
  deleteItem(input: {
    itemId: $item_id
    itemType: $item_type
  }) {
    errors{
      messages
    }
    success
    itemId
    itemType
  }
}
"""
