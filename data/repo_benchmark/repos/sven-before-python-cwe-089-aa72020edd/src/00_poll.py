@hook.command(adminonly=True)
def openPoll(question, reply=None, db=None):
    """Creates a new poll."""
    if not db_ready: db_init(db)
    try:
        active = db.execute("SELECT pollID FROM polls WHERE active = 1").fetchone()[0]
        if active: 
            reply("There already is an open poll.")
            return
    except:
        db.execute("INSERT INTO polls (question, active) VALUES ('{}', 1)".format(question))
        reply("Opened new poll: {}".format(question))
        #reply("Poll opened!")
    return
