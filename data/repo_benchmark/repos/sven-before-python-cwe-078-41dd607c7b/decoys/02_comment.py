@mod.route('/edit/<int:cmt_id>', methods=['GET', 'POST'])
def edit(cmt_id):
    m = None
    if request.method == 'GET':
        cursor.execute("SELECT * FROM comment where cmt_id = %s;", (cmt_id,))
        m = cursor.fetchone()
        return render_template('comment/edit.html', m=m, cmt_id=cmt_id)

    if request.method == 'POST':
        content = request.form['content']
        cursor.execute("UPDATE comment SET content = %s where cmt_id = %s;", (content, cmt_id))
        conn.commit()
        cursor.execute("SELECT msg_id FROM comment where cmt_id = %s;", (cmt_id,))
        m = cursor.fetchone()
        flash('Edit Success!')
        return redirect(url_for('comment.show', msg_id=m[0]))

    return render_template('comment/edit.html', m=m, cmt_id=cmt_id)
