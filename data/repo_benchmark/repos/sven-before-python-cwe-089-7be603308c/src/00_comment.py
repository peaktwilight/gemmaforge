@mod.route('/delete/<int:cmt_id>', methods=['GET', 'POST'])
def delete(cmt_id):
    if request.method == 'GET':
        sql = "SELECT msg_id FROM comment where cmt_id = %d;" % (cmt_id)
        cursor.execute(sql)
        m = cursor.fetchone()
        sql = "DELETE FROM comment where cmt_id = '%d';" % (cmt_id)
        cursor.execute(sql)
        conn.commit()
        flash('Delete Success!')
    return redirect(url_for('comment.show', msg_id=m[0]))
