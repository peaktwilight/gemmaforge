def new_category(category_name):
    try:
        conn = check_heroku_db()
        cur = conn.cursor()
        cur.execute('''INSERT INTO categories (cat_name) VALUES (%s)''', (category_name,))
        conn.commit()
        conn.close()

    except psycopg2.DatabaseError as e:
        print('Error %s' % e)
        sys.exit(1)
