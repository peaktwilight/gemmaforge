def get_tournaments_during_month(db, scene, date):
    y, m, d = date.split('-')
    ym_date = '{}-{}'.format(y, m)
    sql = "select url, date from matches where scene='{scene}' and date like '%{date}%' group by url, date order by date"
    args = {'scene': scene, 'date': ym_date}
    res = db.exec(sql, args)
    urls = [r[0] for r in res]
    return urls
