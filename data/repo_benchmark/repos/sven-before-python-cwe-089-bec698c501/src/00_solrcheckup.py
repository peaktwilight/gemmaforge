def get_old_sourcebyinstitution_number(conn, sqlite, sourcebyinstitution):
    """
    Get all the old sourcebyinstitution number from the SQLite database.
    """
    query = """
        SELECT
            titles
        FROM
            history
        WHERE
            sourcebyinstitution = "%s"
        ORDER BY
            titles DESC
        LIMIT 1
    """ % sourcebyinstitution

    sqlite.execute(query)
    for record in sqlite:
        old_sourcebyinstitution_number = record[0]
        return old_sourcebyinstitution_number
