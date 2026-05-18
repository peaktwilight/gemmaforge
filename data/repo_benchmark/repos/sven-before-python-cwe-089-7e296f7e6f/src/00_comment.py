@mod.route('/edit/<int:cmt_id>', methods=['GET', 'POST'])
def edit(cmt_id):
    m = None
    if request.method == 'GET':
        sql = "SELECT * FROM comment where cmt_id = %d;" % (cmt_id)
        cursor.execute(sql)
        m = cursor.fetchone()
        return render_template('comment/edit.html', m=m, cmt_id=cmt_id)

    if request.method == 'POST':
        content = request.form['content']
        sql = "UPDATE comment SET content = '%s' where cmt_id = '%d';" \
            % (content, cmt_id)
        cursor.execute(sql)
        conn.commit()
        sql = "SELECT msg_id FROM comment where cmt_id = %d;" % (cmt_id)
        cursor.execute(sql)
        m = cursor.fetchone()
        flash('Edit Success!')
        return redirect(url_for('comment.show', msg_id=m[0]))

    return render_template('comment/edit.html', m=m, cmt_id=cmt_id)
