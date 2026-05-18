def markTokenUsedExternal(token, optStr=""):
    conn, c = connectDB()
    req = "UPDATE {} SET \"options_selected\"=? WHERE token=?".format(CFG("tokens_table_name"))
    c.execute(req, (optStr, token,))
    closeDB(conn)
