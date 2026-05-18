def get_first_ranked_month(db, scene, player):
    sql = "select date from ranks where scene='{}' and player='{}' order by date limit 1;".format(scene, player)
    res = db.exec(sql)
    date = res[0][0]
    return date
