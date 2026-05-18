def check(current_num):
    try:
        cursor.execute('SELECT * FROM comics WHERE num=?', (current_num,))
    except sqlite3.OperationalError:
        cursor.execute('CREATE TABLE comics (num text)')
        return False
    else:
        return False if cursor.fetchone() is None else True
