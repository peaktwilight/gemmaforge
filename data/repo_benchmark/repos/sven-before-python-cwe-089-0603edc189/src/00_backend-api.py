def addTags(tag_list, listing_id):
    """
    Adds a list of tags tag_list for a given listing with listing_id to the database
    """
    cur = conn.cursor()
    for x in tag_list:
        sql = "INSERT INTO {} VALUES {}".format(listing_tags_table_name, str((listing_id, x)))
        cur.execute(sql)
