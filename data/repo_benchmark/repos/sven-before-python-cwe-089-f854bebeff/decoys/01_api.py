@app.route('/top_proxies')
def top_proxies():
    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT sum(amount) FROM holders"
    cur.execute(query)
    total = cur.fetchone()
    total_votes = total[0]

    query = "SELECT voting_as FROM holders WHERE voting_as<>'1.2.5' group by voting_as"
    cur.execute(query)
    results = cur.fetchall()
    #con.close()

    proxies = []

    for p in range(0, len(results)):

        proxy_line = [0] * 5

        proxy_id = results[p][0]
        proxy_line[0] = proxy_id

        query = "SELECT account_name, amount FROM holders WHERE account_id=%s LIMIT 1"
        cur.execute(query, (proxy_id,))
        proxy = cur.fetchone()

        try:
            proxy_name = proxy[0]
            proxy_amount = proxy[1]
        except:
            proxy_name = "unknown"
            proxy_amount = 0


        proxy_line[1] = proxy_name

        query = "SELECT amount, account_id FROM holders WHERE voting_as=%s"
        cur.execute(query, (proxy_id,))
        results2 = cur.fetchall()

        proxy_line[2] = int(proxy_amount)

        for p2 in range(0, len(results2)):
            amount = results2[p2][0]
            account_id = results2[p2][1]
            proxy_line[2] = proxy_line[2] + int(amount)  # total proxy votes
            proxy_line[3] = proxy_line[3] + 1       # followers

        if proxy_line[3] > 2:
            percentage = float(float(proxy_line[2]) * 100.0/ float(total_votes))
            proxy_line[4] = percentage
            proxies.append(proxy_line)

    con.close()

    proxies = sorted(proxies, key=lambda k: int(k[2]))
    r_proxies = proxies[::-1]

    return jsonify(filter(None, r_proxies))
