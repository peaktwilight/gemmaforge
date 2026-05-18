def getResults(poll_name):
    conn, c = connectDB()
    req = "SELECT options from {} where name=?".format(CFG("poll_table_name"))
    options_str = queryOne(c, req, (poll_name,))

    if not options_str:
        raise LookupError("Poll '{}' not found in DB".format(poll_name))

    total = 0
    options = options_str.split(",")
    results = dict()
    for opt in options:
        count = getOptionCount(c, poll_name, opt)
        total += int(count)
        results.update({opt:count})

    conn.close()
    return (results, total)
