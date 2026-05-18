def get_first_month(db, scene):
    sql = "select date from matches where scene='{scene}' order by date limit 1;"
    args = {'scene': scene}
    res = db.exec(sql, args)
    date = res[0][0]
    return date
