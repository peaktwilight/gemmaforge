@mod.route('/like/<int:msg_id>', methods=['GET', 'POST'])
def like(msg_id):
    if request.method == 'GET':
        user_id = session['logged_id']
        c_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO like_msg(msg_id, user_id,c_time) VALUES(%s,%s,%s);", (msg_id, user_id, c_time))
        conn.commit()
    return redirect(url_for('show_entries'))
