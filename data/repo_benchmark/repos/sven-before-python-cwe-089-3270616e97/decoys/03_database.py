def GameNewPlayed(Played, ID):
	db.execute("UPDATE games set GamesPlayed = ? WHERE ID = ?", Played, ID)
	database.commit()
