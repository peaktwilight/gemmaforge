def get_first_month(db, scene):
    sql = "select date from matches where scene='{}' order by date limit 1;".format(scene)
    res = db.exec(sql)
    date = res[0][0]
    return date
