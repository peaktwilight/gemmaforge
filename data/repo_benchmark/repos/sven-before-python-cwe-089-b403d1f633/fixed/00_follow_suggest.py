def _get_degree_2(user_id, cnx):
    """Get all users of degree 2 follow that are not currently followed.
    Example:
        this user (follows) user B (follows) user B
        AND user (does NOT follow) user B
        means that user B will be in the list
    Args:
        user_id (int): id of user
        cnx: DB connection
    Returns:
        list: list of user_ids
    """
    sql = 'WITH tmp_suggest (followed_id) AS ' \
    '(' \
        'SELECT b.followed_id AS followed_id ' \
        'FROM ' \
            'tbl_follow a INNER JOIN tbl_follow b ' \
            'ON a.followed_id = b.follower_id ' \
        'WHERE a.follower_id = %s ' \
        'AND b.followed_id NOT IN ' \
            '(SELECT followed_id FROM tbl_follow WHERE follower_id = %s) ' \
        'AND b.followed_id != %s ' \
    ') ' \
    'SELECT followed_id, COUNT(*) AS num_mutual FROM tmp_suggest ' \
    'GROUP BY followed_id ' \
    'ORDER BY num_mutual DESC'
    with cnx.cursor() as cursor:
        cursor.execute(sql, (user_id, user_id, user_id))
        res = cursor.fetchall()
    return list(map(lambda x: x[0], res))
