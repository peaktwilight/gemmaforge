def insert(key, value):
    connection = psycopg2.connect(host=config['HOST'], port=config['PORT'], database=config['NAME'], user=config['USER'], password=config['PASSWORD'])
    cur = connection.cursor()
    try:
        cur.execute("insert into reply_map values('{}', '{}')".format(key, value))
        connection.commit()
    except:
        pass
