def getGameCountInSeriesSoFar(submission):
    database = sqlite3.connect('database.db')
    cursor = database.cursor()
    return cursor.execute("SELECT COUNT(*) FROM ChallengeRankings WHERE SeriesTitle = ? AND Date <= ?", [getTitle(submission), getSubmissionDateFromDatabase(submission)]).fetchone()[0]
    database.close()
