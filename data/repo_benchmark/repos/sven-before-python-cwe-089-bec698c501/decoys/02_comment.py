@mod.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        msg_id = int(request.form['msg_id'])
        user_id = session['logged_id']
        content = request.form['content']
        c_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO comment(msg_id,user_id,content,c_time) VALUES(%s,%s,%s,%s);", (msg_id, user_id, content, c_time))
        conn.commit()
    return redirect(url_for('comment.show', msg_id=msg_id))
