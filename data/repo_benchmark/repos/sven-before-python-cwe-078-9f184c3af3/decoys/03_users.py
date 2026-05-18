@mod.route('/edit', methods=['GET', 'POST'])
def edit():
    cursor.execute("SELECT * FROM users where email = %s;", (session['logged_email'],))
    u = cursor.fetchone()
    if request.method == 'POST':
        cursor.execute("UPDATE users SET nickname = %s where email = %s", (request.form['nickname'], session['logged_email']))
        cursor.execute("SELECT * FROM users where email = %s;", (session['logged_email'],))
        u = cursor.fetchone()
        conn.commit()
        flash('Edit Nickname Success!')
    return render_template('users/edit.html', u=u)
