@mod.route('/delete/<int:msg_id>', methods=['GET', 'POST'])
def delete(msg_id):
    if request.method == 'GET':
        cursor.execute("DELETE FROM message where msg_id = %s;", (msg_id,))
        conn.commit()
        flash('Delete Success!')
    return redirect(url_for('show_entries'))
