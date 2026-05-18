def getSeriesDateFromDatabase(submission):
    database = sqlite3.connect('database.db')
    cursor = database.cursor()
    return cursor.execute("SELECT StartDate FROM SeriesTracking WHERE SeriesTitle = '" + str(getTitle(submission)) + "'").fetchone()[0]
    database.close()
