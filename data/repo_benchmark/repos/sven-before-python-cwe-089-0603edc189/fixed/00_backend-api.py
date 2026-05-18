def addTags(tag_list, listing_id):
    """
    Adds a list of tags tag_list for a given listing with listing_id to the database
    """
    cur = conn.cursor()
    for x in tag_list:
        sql = "INSERT INTO %s VALUES (%s %s)"
        cur.execute(sql, (listing_tags_table_name, listing_id, x))
