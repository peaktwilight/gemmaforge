def retrieve_videos_from_playlist(playlist_id, db):
    db.execute("SELECT id, title, thumbnail, position from video WHERE playlist_id=%s ORDER BY position ASC;", (playlist_id,))
    rows = db.fetchall()
    return rows
