def create_playlist(name, db):
    db.execute(
        "INSERT INTO playlist (name, video_position) VALUES('{name}', 0);".format(name=name))
