def retrieve_videos_from_playlist(playlist_id, db):
    db.execute("SELECT id, title, thumbnail, position from video WHERE playlist_id={playlist_id} ORDER BY position ASC;".format(
        playlist_id=playlist_id))
    rows = db.fetchall()
    return rows
