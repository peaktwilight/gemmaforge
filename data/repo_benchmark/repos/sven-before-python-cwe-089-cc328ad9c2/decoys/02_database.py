def getOptions(poll_name):
    conn, c = connectDB()
    req = "SELECT options FROM {} WHERE name=?".format(CFG("poll_table_name"))
    options_str = queryOne(c, req, (poll_name,))
    if options_str == None:
        return None
    options = options_str.split(",")
    closeDB(conn)
    return options
