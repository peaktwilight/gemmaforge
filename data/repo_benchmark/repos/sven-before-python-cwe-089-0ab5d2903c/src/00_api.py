@app.route('/lookup_assets')
def lookup_assets():
    start = request.args.get('start')

    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT aname FROM assets WHERE aname LIKE '"+start+"%'"
    cur.execute(query)
    results = cur.fetchall()
    con.close()
    return jsonify(results)
