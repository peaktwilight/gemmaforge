  def fetch_page_name(self, page_id):
    '''
    Returns the page name corresponding to the provided page ID.

    Args:
      page_id: The page ID whose ID to fetch.

    Returns:
      str: The page name corresponding to the provided page ID.

    Raises:
      ValueError: If the provided page ID is invalid or does not exist.
    '''
    helpers.validate_page_id(page_id)

    query = 'SELECT name FROM pages WHERE id="{0}"'.format(page_id)
    self.cursor.execute(query)

    page_name = self.cursor.fetchone()

    if not page_name:
      raise ValueError('Invalid page ID "{0}" provided. Page ID does not exist.'.format(page_id))

    return page_name[0].encode('utf-8').replace('_', ' ')
