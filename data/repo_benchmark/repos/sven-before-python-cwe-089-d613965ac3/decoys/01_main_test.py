def create_playlist(name):
    db = connect_to_database()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO playlist (name, video_position) VALUES(%s, 0);", (name,))
    db.commit()
    db.close()
