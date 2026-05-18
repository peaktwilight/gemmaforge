@mod.route('/test', methods=['GET', 'POST'])
def test():
    user_id = session['logged_id']
    sql = 'SELECT * FROM message where user_id = %d ORDER BY c_time DESC' \
        % (user_id)
    cursor.execute(sql)
    m = cursor.fetchall()
    print(m)
