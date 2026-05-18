def update_playlist(id, name, db):
    db.execute("UPDATE playlist SET name=%s WHERE id=%s;", (name, id,))
