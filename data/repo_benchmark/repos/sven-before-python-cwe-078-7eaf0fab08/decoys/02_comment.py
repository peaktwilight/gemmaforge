@mod.route('/delete/<int:cmt_id>', methods=['GET', 'POST'])
def delete(cmt_id):
    if request.method == 'GET':
        cursor.execute("SELECT msg_id FROM comment where cmt_id = %s;", (cmt_id,))
        m = cursor.fetchone()
        cursor.execute("DELETE FROM comment where cmt_id = %s;", (cmt_id,))
        conn.commit()
        flash('Delete Success!')
    return redirect(url_for('comment.show', msg_id=m[0]))
