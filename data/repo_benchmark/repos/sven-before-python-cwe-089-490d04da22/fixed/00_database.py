def insertUsage(user, command):
	c, conn = getConnection()
	date = now()
	c.execute("INSERT INTO usage (date,user,command) VALUES (?,?,?)",(date,str(user),command))
	conn.commit()
	conn.close()
