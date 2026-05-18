def get_monthly_ranks_for_scene(db, scene, tag):

    sql = "SELECT date, rank FROM ranks WHERE scene='{scene}' AND player='{tag}'"
    args = {'scene': scene, 'tag': tag}
    res = db.exec(sql, args)

    res = [r for r in res if played_during_month(db, scene, tag, get_previous_month(r[0]))]

    # Build up a dict of {date: rank}
    ranks = {}
    for r in res:
        ranks[r[0]] = r[1]

    return ranks
