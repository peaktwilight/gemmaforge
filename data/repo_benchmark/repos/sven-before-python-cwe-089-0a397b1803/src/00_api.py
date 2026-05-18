@app.route('/get_all_referrers')
def get_all_referrers():
    account_id = request.args.get('account_id')

    if not isObject(account_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_account_names",[["' + account_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)

        account_id = j_l["result"][0]["id"]

    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "select * from referrers where referrer='"+account_id+"'"
    cur.execute(query)
    results = cur.fetchall()

    return jsonify(results)
