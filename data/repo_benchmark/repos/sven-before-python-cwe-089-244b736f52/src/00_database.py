def markTokenUsedExternal(token, optStr=""):
    conn, c = connectDB()
    req = "UPDATE {} SET \"options_selected\"='{}' WHERE token='{}'".format(CFG("tokens_table_name"), \
                    optStr, token)
    c.execute(req)
    closeDB(conn)
