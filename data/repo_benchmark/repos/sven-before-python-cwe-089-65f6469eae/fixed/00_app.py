@app.route('/', methods=['POST'])
def login():
    print('login')
    user = str(request.form['username'])
    password = str(request.form['password'])
    cur.execute("SELECT * FROM users WHERE name = ? AND password = ?;", [user, password])
    response = cur.fetchone()
    if response != None:
        print(response, 'OK')
        return redirect(url_for('enter_test_point'))
    else:
        print(response, 'not OK')
        flash('Invalid login or password')
        return render_template('login.html')
