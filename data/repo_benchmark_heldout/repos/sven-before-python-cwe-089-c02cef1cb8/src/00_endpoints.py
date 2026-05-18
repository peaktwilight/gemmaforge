@endpoints.route("/h2h")
def h2h():
    if db == None:
        init()

    player1 = request.args.get('tag1', default="christmasmike")
    player2 = request.args.get('tag2', default="christmasmike")
    sql = "SELECT * FROM matches WHERE (player1 = '"+str(player1)+"' OR "\
            +"player2 = '"+str(player1)+"') AND (player1 = '"+str(player2)+"' OR "\
            +"player2 = '"+str(player2)+"') ORDER BY date DESC;"
    result = db.exec(sql)
    return json.dumps(result)
