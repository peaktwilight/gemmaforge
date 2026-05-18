def getSubmissionDateFromDatabase(submission):
    database = sqlite3.connect('database.db')
    cursor = database.cursor()
    return cursor.execute("SELECT Date FROM ChallengeRankings WHERE SubmissionID = ?", [str(submission.id)]).fetchone()[0]
    database.close()
