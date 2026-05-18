def getGameID(ID):
	db.execute("SELECT * FROM games WHERE ID = %i" % ID)
	ID = db.fetchone()
	return ID
