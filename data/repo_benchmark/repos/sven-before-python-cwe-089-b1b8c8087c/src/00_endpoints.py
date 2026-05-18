@endpoints.route("/ranks")
def ranks():
    if db == None:
        init()

    scene = request.args.get('scene', default='austin')
    date = request.args.get('date')
 
    # If no date was provided, pick the date of the latest tournament
    if date == None:
        sql = "SELECT distinct date FROM ranks WHERE scene='{}' ORDER BY date DESC LIMIT 1;".format(scene)
        res = db.exec(sql)
        date = res[0][0]

    # Get all the urls that this player has participated in
    sql = "SELECT * FROM ranks WHERE scene = '{}' and date='{}'".format(scene, date)
    res = db.exec(sql)

    # Make a dict out of this data
    # eg {'christmasmike': 50}
    cur_ranks = {}
    for r in res:
        tag = r[1]
        rank = r[2]

        cur_ranks[tag] = rank

    # Now get the ranks from last month, so we know if these players went up or down
    y, m, d = date.split('-')
    prev_date = bracket_utils.get_previous_month(date)

    # Get all the urls that this player has participated in
    sql = "SELECT * FROM ranks WHERE scene = '{}' and date='{}'".format(scene, prev_date)
    res = db.exec(sql)

    # Make a dict out of this data
    # eg {'christmasmike': 50}
    prev_ranks = {}
    for r in res:
        tag = r[1]
        rank = r[2]

        prev_ranks[tag] = rank

    return render_template('libraries/html/ranks.html', cur_ranks=cur_ranks, prev_ranks=prev_ranks, scene=scene, date=date)
