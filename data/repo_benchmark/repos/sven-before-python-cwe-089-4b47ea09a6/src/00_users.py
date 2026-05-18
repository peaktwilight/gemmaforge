@mod.route('/edit', methods=['GET', 'POST'])
def edit():
    sql = "SELECT * FROM users where email = '%s';" % (session['logged_email'])
    cursor.execute(sql)
    u = cursor.fetchone()
    if request.method == 'POST':
        sql = "UPDATE users SET nickname = '%s' where email = '%s'" \
        % (request.form['nickname'], session['logged_email'])
        cursor.execute(sql)
        sql = "SELECT * FROM users where email = '%s';" \
            % (session['logged_email'])
        cursor.execute(sql)
        u = cursor.fetchone()
        conn.commit()
        flash('Edit Nickname Success!')
    return render_template('users/edit.html', u=u)
