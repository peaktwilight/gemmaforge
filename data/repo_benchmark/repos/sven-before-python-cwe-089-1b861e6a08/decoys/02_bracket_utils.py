def get_bracket_graph_data(db, tag):
    # First, we have to find out which scenes this player has brackets in
    sql = "SELECT DISTINCT scene FROM ranks WHERE player='{tag}'"
    args = {'tag': tag}
    scenes = db.exec(sql, args)
    scenes = [s[0] for s in scenes]

    bracket_placings_by_scene = {s: get_bracket_placings_in_scene(db, s, tag) for s in scenes}

    return bracket_placings_by_scene
