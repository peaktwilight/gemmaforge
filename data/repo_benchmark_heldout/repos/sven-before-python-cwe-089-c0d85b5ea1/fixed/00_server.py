def fetch_issue(cursor, id):
    """
    Fetch an issue by id along with its tags. Returns None if no issue
    with the specified id exists in the database.
    """
    cursor.execute("""
        SELECT
            issue.id,
            issue.title,
            issue.description,
            tag.namespace,
            tag.predicate,
            tag.value
        FROM
            issue LEFT JOIN tag
            ON issue.id = tag.issue_id
        WHERE
            issue.id = ?
    """, (id,))

    issue = None
    for row in cursor:
        if issue is None:
            issue = {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "tags": [],
            }
        # If tag exists in row, add to issue.
        if row["value"]:
            issue["tags"].append({
                "namespace": row["namespace"],
                "predicate": row["predicate"],
                "value": row["value"],
            })

    return issue
