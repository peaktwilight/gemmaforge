@hook.command(autohelp=False)
def showPoll(pollID, db=None):
    """Shows the answers for a given poll."""
    if not db_ready: db_init(db)
    if pollID == None:
        poll = db.execute("SELECT pollID, question FROM polls WHERE active = 1")
        if len(poll) == 0:
            reply("There's no poll open.")
            return
    else:
        poll = db.execute("SELECT pollID, question FROM polls WHERE pollID = ?", (pollID,))
        if len(poll) == 0:
            reply("No such poll found.")
            return
    pollID = poll[0][0]
    question = poll[0][1]
    reply(question)
    for (index, answer, votes) in db.execute("SELECT 'index', answer, count(voteID) FROM answers LEFT JOIN votes ON votes.answerID = answers.answerID WHERE pollID = ? GROUP BY answers.answerID, 'index', answer ORDER BY 'index' ASC", (pollID, )):
        reply("%s. %s (%s)" % (index, answer, votes))
