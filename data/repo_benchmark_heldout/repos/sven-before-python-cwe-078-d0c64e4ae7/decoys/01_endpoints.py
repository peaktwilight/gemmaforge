@endpoints.route("/wins")
def wins():
    if db == None:
        init()

    player = request.args.get('tag', default="christmasmike")
    sql = "SELECT * FROM matches WHERE winner = '{player}' ORDER BY date DESC;"
    args = {'player': player}
    result = db.exec(sql, args)

    result = [str(x) for x in result]
    result = '\n'.join(result)
    return json.dumps(result)
