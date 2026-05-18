@endpoints.route("/h2h")
def h2h():
    if db == None:
        init()

    player1 = request.args.get('tag1', default="christmasmike")
    player2 = request.args.get('tag2', default="christmasmike")
    sql = "SELECT * FROM matches WHERE (player1 = '{player1}' OR "\
            +"player2 = '{player1}') AND (player1 = '{player2}' OR "\
            +"player2 = '{player2}') ORDER BY date DESC;"
    args = {'player1': player1, 'player2': player2}
    result = db.exec(sql, args)
    return json.dumps(result)
