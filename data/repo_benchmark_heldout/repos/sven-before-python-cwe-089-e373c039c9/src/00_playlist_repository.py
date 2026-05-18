def retrieve_playlist_by_id(id, db):
    db.execute(
        "SELECT id, name, video_position from playlist WHERE id={id};".format(id=id))
    row = db.fetchone()
    return row
