def get_tournaments_during_month(db, scene, date):
    y, m, d = date.split('-')
    ym_date = '{}-{}'.format(y, m)
    sql = "select url, date from matches where scene='{}' and date like '%{}%' group by url, date order by date".format(scene, ym_date)
    res = db.exec(sql)
    urls = [r[0] for r in res]
    return urls
