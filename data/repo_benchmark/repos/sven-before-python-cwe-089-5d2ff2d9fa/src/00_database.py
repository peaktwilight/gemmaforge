def closeGame(ID):
	db.execute("UPDATE games set Running = 'No' WHERE ID = %i" % ID)
	database.commit()
