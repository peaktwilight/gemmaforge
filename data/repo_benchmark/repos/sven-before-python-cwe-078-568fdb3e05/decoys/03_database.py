def isValidAdmToken(adm_token):
    conn, c = connectDB()
    req = "SELECT *  from {} where adm_token=?".format(CFG("admintoken_table_name"))
    answer = bool(queryOne(c, req, (adm_token,)))
    closeDB(conn)
    return answer
