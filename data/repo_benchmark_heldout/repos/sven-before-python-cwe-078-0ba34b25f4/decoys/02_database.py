def insertNPC(name, race,classe,sex,level,image,legit):
	c, conn = getConnection()
	date = now()
	c.execute("INSERT INTO npc VALUES (?,?,?,?,?,?,?,?)",(date,str(name),race,classe,sex,str(level),image,str(legit)))
	conn.commit()
	conn.close()
