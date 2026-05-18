@mod.route('/edit/<int:msg_id>', methods=['GET', 'POST'])
def edit(msg_id):
    m = None
    if request.method == 'GET':
        cursor.execute("SELECT * FROM message where msg_id = %s;", (msg_id,))
        m = cursor.fetchone()
        return render_template('message/edit.html', m=m, msg_id=msg_id)

    if request.method == 'POST':
        content = request.form['content']
        cursor.execute("UPDATE message SET content = %s where msg_id = %s;", (content, msg_id))
        conn.commit()
        flash('Edit Success!')
        return redirect(url_for('show_entries'))

    return render_template('message/edit.html', m=m, msg_id=msg_id)
