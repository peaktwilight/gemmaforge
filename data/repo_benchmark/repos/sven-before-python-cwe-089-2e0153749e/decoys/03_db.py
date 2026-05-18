def new_category(category_name):
    try:
        conn = check_heroku_db()
        cur = conn.cursor()

        query = "INSERT INTO categories (cat_name) VALUES (%s);"
        data = (category_name,)
        cur.execute(query, data)

        conn.commit()
        conn.close()

    except psycopg2.DatabaseError as e:
        print('Error %s' % e)
        sys.exit(1)
