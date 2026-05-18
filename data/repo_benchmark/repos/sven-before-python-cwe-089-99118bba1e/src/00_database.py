def getPlayer(player):
	db.execute("SELECT * FROM players WHERE Name = '%s' COLLATE NOCASE" % player)
	playerstats = dict(db.fetchone())
	return playerstats
