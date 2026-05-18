def get_top_popular(top_num):
    """ query the top(top_num) popular articles
        top_num => list of [title, count]
    """
    cmd = """SELECT title, views FROM articles
             INNER JOIN (
             SELECT path, count(path) AS views
             FROM log GROUP BY log.path
             ) AS log
             ON log.path = '/article/' || articles.slug
             ORDER BY views DESC
             LIMIT %s"""
    data = [top_num, ]
    return execute_query(cmd, data)
