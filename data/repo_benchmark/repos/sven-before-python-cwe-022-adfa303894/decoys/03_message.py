@mod.route('/test', methods=['GET', 'POST'])
def test():
    user_id = session['logged_id']
    cursor.execute('SELECT * FROM message where user_id = %s ORDER BY c_time DESC', (user_id,))
    m = cursor.fetchall()
    print(m)
