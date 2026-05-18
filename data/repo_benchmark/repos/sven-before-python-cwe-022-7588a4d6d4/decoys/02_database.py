def findNPC(race, classe, sex,level):
	c, conn = getConnection()
	date = now()
	#select image, SUM(legit) as l FROM npc WHERE race='Elf' AND class='Bard' AND sex='Male' GROUP BY image HAVING l>5 ORDER BY SUM(legit) DESC;
	c.execute("select image, avg(legit) as l FROM npc WHERE race=(?) AND class=(?) AND sex=(?) GROUP BY image HAVING l > 5 ORDER BY SUM(legit) DESC",(race,classe,sex))
	conn.commit()
	out = c.fetchmany(5)
	conn.close()
	return out
