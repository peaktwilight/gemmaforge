def incrementOption(cursor, poll_name, option):
    key = poll_name+"-"+option
    req = "UPDATE {} SET count=count+1 WHERE name_option=?".format(CFG("options_table_name"))
    cursor.execute(req, (key,))
