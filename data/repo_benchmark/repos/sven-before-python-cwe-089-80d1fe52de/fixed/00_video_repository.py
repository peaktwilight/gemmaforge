def delete_playlists_videos(playlist_id, db):
    db.execute("DELETE FROM video where playlist_id=%s;", (playlist_id,))
