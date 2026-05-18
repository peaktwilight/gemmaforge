@mod.route('/delete/<int:msg_id>', methods=['GET', 'POST'])
def delete(msg_id):
    if request.method == 'GET':
        sql = "DELETE FROM message where msg_id = '%d';" % (msg_id)
        cursor.execute(sql)
        conn.commit()
        flash('Delete Success!')
    return redirect(url_for('show_entries'))
