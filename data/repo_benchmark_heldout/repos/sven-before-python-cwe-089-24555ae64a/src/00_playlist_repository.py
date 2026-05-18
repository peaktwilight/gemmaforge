def update_playlist(id, name, db):
    db.execute(
        "UPDATE playlist SET name='{name}' WHERE id={id};".format(name=name, id=id))
