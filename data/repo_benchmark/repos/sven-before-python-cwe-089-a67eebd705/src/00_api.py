@app.route('/referrer_count')
def referrer_count():
    account_id = request.args.get('account_id')

    if not isObject(account_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_account_names",[["' + account_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)

        account_id = j_l["result"][0]["id"]

    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "select count(*) from referrers where referrer='"+account_id+"'"
    cur.execute(query)
    results = cur.fetchone()

    return jsonify(results)
