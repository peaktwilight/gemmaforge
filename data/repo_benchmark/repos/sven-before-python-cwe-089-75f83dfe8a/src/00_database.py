def isValidAdmToken(adm_token):
    conn, c = connectDB()
    req = "SELECT *  from {} where adm_token='{}'".format(CFG("admintoken_table_name"), adm_token)
    answer = bool(queryOne(c, req))
    closeDB(conn)
    return answer
