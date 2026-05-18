@mod.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        error = None
        email = request.form['email'].strip()
        nickname = request.form['nickname'].strip()
        password = request.form['password'].strip()
        password2 = request.form['password2'].strip()

        email = email.lower()

        if email == "" or nickname == "" or password == "" or password2 == "":
            error = 'Please input all the information'
        elif password2 != password:
            error = 'The password is not repeated correctly'
        elif len(password) < 6:
            error = 'The password has at least 6 characters'
        elif not re.match(r'^[0-9a-zA-Z_]{0,19}@' +
                          '[0-9a-zA-Z]{1,15}\.[com,cn,net]', email):
            error = 'Please input the right email'

        sql = "SELECT * FROM users where email = '%s';" % (email)
        cursor.execute(sql)
        u = cursor.fetchone()

        if u is not None:
            error = 'The email has already exsit'

        if error is not None:
            return render_template('register.html', error=error)
        else:
            password = bcrypt.generate_password_hash(password)
            cursor.execute("INSERT INTO users(email,nickname,password) VALUES(%s,%s,%s);", (email, nickname, password))
            conn.commit()
            flash('Register Success!')
            return redirect(url_for('users.login'))

    return render_template('register.html')
