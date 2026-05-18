def get_article(index):
    with conn.cursor(cursor_factory=DictCursor) as cur:
        query = "SELECT * FROM articles WHERE index="+str(index)
        cur.execute(query)
        article = cur.fetchone()
        return article
