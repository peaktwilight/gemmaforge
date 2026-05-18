def getGameID(ID):
	db.execute("SELECT * FROM games WHERE ID = ?", ID)
	ID = db.fetchone()
	return ID
