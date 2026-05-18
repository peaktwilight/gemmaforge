def retrieve_video(id, playlist_id, db):
    db.execute(
        "SELECT id, position from video WHERE id=%s and playlist_id=%s;", (id, playlist_id))
    row = db.fetchone()
    return row
