def add_post(content):
  """Add a post to the 'database' with the current timestamp."""
  conn = psycopg2.connect("dbname=forum")
  cursor = conn.cursor()
  one_post = content
  cursor.execute("insert into posts values (%s)", (one_post,))
  conn.commit()
  conn.close()
