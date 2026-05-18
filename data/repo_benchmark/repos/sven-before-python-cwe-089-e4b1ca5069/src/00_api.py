@app.route('/get_markets')
def get_markets():
    asset_id = request.args.get('asset_id')

    if not isObject(asset_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_asset_symbols",[["' + asset_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)
        asset_id = j_l["result"][0]["id"]


    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT * FROM markets WHERE aid='"+asset_id+"'"
    cur.execute(query)
    results = cur.fetchall()
    con.close()
    return jsonify(results)
