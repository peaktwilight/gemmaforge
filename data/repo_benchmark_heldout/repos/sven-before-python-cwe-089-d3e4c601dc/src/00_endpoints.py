@endpoints.route("/wins")
def wins():
    if db == None:
        init()

    player = request.args.get('tag', default="christmasmike")
    sql = "SELECT * FROM matches WHERE winner = '"+str(player)+"' ORDER BY date DESC;"
    result = db.exec(sql)

    result = [str(x) for x in result]
    result = '\n'.join(result)
    return json.dumps(result)
