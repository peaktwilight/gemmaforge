def retrieve_video(id, playlist_id, db):
    db.execute("SELECT id, position from video WHERE id={id} and playlist_id={playlist_id};".format(
        id=id, playlist_id=playlist_id))
    row = db.fetchone()
    return row
