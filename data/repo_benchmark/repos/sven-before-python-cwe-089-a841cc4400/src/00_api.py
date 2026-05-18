@app.route('/get_asset_and_volume')
def get_asset_and_volume():
    asset_id = request.args.get('asset_id')

    if not isObject(asset_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_asset_symbols",[["' + asset_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)
        asset_id = j_l["result"][0]["id"]

    #print asset_id
    ws.send('{"id":1, "method":"call", "params":[0,"get_assets",[["' + asset_id + '"], 0]]}')
    result = ws.recv()
    j = json.loads(result)

    dynamic_asset_data_id =  j["result"][0]["dynamic_asset_data_id"]

    ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["'+dynamic_asset_data_id+'"]]]}')
    result2 = ws.recv()
    j2 = json.loads(result2)
    #print j2["result"][0]["current_supply"]

    j["result"][0]["current_supply"] = j2["result"][0]["current_supply"]
    j["result"][0]["confidential_supply"] = j2["result"][0]["confidential_supply"]
    #print j["result"]

    j["result"][0]["accumulated_fees"] = j2["result"][0]["accumulated_fees"]
    j["result"][0]["fee_pool"] = j2["result"][0]["fee_pool"]

    issuer = j["result"][0]["issuer"]
    ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["'+issuer+'"]]]}')
    result3 = ws.recv()
    j3 = json.loads(result3)
    j["result"][0]["issuer_name"] = j3["result"][0]["name"]


    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT volume, mcap FROM assets WHERE aid='"+asset_id+"'"
    cur.execute(query)
    results = cur.fetchall()
    con.close()
    try:
        j["result"][0]["volume"] = results[0][0]
        j["result"][0]["mcap"] = results[0][1]
    except:
        j["result"][0]["volume"] = 0
        j["result"][0]["mcap"] = 0

    return jsonify(j["result"])
