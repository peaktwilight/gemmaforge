@app.route('/summary', methods=['GET'])
def summary():
	if 'username' in session:

		conn = mysql.connect()
		cursor = conn.cursor()

		#select the maximum score from the results table
		cursor.execute("SELECT courseConcentration FROM results WHERE total = (SELECT MAX(total) FROM (SELECT * FROM results WHERE courseId > 4) Temp) and courseId > 4 and emailAccount='" + session['username'] + "'");
		courseConcentration = cursor.fetchone()

		return render_template('summary.html', courseConcentration = courseConcentration[0])
	return redirect(url_for('login'))
