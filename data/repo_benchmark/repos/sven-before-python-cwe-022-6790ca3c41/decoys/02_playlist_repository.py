def create_playlist(name, db):
    db.execute(
        "INSERT INTO playlist (name, video_position) VALUES(%s, 0);", (name,))
