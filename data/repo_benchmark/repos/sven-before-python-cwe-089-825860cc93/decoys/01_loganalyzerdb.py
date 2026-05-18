def get_top_author(top_num):
    """ query the top(top_num) popular author
        top_num => list of [author, count]
    """
    cmd = """SELECT authors.name,author_result.num
                    FROM authors JOIN
                    (SELECT SUM(article_result.num) as num,
                    article_result.author
                    from (SELECT articles.title, articles.author,
                    SUM(log.views) AS num
                    FROM articles
                    INNER JOIN (
                    SELECT path, count(path) AS views
                    FROM log GROUP BY log.path
                    ) AS log ON log.path = '/article/'
                    || articles.slug
                    GROUP BY articles.title, articles.author)
                    AS article_result
                    GROUP BY article_result.author) as author_result
                    ON authors.id = author_result.author
                    ORDER BY num DESC LIMIT %s"""
    data = [top_num, ]
    return execute_query(cmd, data)
