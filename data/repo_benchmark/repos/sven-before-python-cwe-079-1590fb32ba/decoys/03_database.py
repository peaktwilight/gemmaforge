def closeGame(ID):
	db.execute("UPDATE games set Running = 'No' WHERE ID = ?", ID)
	database.commit()
