def GameNewPlayed(Played, ID):
	db.execute("UPDATE games set GamesPlayed = %i WHERE ID = %i" % (Played, ID))
	database.commit()
