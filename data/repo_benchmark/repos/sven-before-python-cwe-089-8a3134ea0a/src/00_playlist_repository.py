def delete_playlist(id, db):
    db.execute("DELETE FROM playlist where id={id};".format(id=id))
