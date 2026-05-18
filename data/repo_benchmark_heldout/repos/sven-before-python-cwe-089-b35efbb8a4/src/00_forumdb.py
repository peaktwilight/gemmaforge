def add_post(content):
  """Add a post to the 'database' with the current timestamp."""
  conn = psycopg2.connect("dbname=forum")
  cursor = conn.cursor()
  cursor.execute("insert into posts values ('%s')" % content)
  conn.commit()
  conn.close()
