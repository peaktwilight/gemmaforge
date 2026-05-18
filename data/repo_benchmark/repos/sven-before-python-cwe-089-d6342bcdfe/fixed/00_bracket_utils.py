def get_first_ranked_month(db, scene, player):
    sql = "select date from ranks where scene='{scene}' and player='{player}' order by date limit 1;"
    args = {'scene': scene, 'player': player}
    res = db.exec(sql, args)
    date = res[0][0]
    return date
