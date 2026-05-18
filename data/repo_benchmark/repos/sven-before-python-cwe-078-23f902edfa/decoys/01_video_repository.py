def retrieve_last_video_position(playlist_id, db):
    db.execute(
        "SELECT max(position) as position from video WHERE playlist_id=%s;", (playlist_id,))
    row = db.fetchone()
    return row['position']
