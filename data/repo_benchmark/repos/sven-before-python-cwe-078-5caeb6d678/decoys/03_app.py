def get_article(index):
    with conn.cursor(cursor_factory=DictCursor) as cur:
        query = "SELECT * FROM articles WHERE index=%s"
        cur.execute(query, (index, ))
        article = cur.fetchone()
        return article
