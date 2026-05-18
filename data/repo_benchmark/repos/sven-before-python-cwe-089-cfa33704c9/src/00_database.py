def makeJudge(judge):
	db.execute("UPDATE players SET Judge = 1 WHERE Name = '%s' COLLATE NOCASE" % (judge)) 
	database.commit()
