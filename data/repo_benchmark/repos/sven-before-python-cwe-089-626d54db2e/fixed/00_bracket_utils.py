def get_last_month(db, scene):
    sql = "select date from matches where scene='{scene}' order by date desc limit 1;"
    args = {'scene': scene}
    res = db.exec(sql, args)
    date = res[0][0]

    # If it has been more than 1 month since this last tournament,
    # go ahead and round this date up by a 1 month
    # eg, if the last tournament was 2015-01-15 (a long time ago)
    # we can assume the scene won't have more tournaments
    # So just round to 2015-02-01
    today = datetime.datetime.today().strftime('%Y-%m-%d')
    y, m, d = today.split('-')
    cy, cm, cd = date.split('-')
    if y > cy or m > cm:
        # Add 1 to the month before we return
        # eg 2018-03-01 -> 2018-04-01
        date = get_next_month(date)

    return date
