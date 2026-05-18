def getGameCountInSeriesSoFar(submission):
    database = sqlite3.connect('database.db')
    cursor = database.cursor()
    return cursor.execute("SELECT COUNT(*) FROM ChallengeRankings WHERE SeriesTitle = '" + getTitle(submission) + "' AND Date <= '" + getSubmissionDateFromDatabase(submission) + "'").fetchone()[0]
    database.close()
