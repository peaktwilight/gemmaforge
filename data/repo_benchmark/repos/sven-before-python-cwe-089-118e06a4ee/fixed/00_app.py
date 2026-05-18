def get_articles_by_subject(subject):
    with conn.cursor(cursor_factory=DictCursor) as cur:
        query = "SELECT * FROM articles WHERE subject=%s ORDER BY last_submitted DESC"
        cur.execute(query, (subject,))
        articles = cur.fetchall()
        return articles
