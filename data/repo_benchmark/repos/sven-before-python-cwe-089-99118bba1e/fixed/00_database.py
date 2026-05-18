def getPlayer(player):
	db.execute("SELECT * FROM players WHERE Name = ? COLLATE NOCASE", player)
	playerstats = dict(db.fetchone())
	return playerstats
