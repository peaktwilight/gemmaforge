@app.route('/overview/<classNum>')
def overview(classNum):
	if 'username' in session:
		classNoSpace = classNum.split(' ')[0]+classNum.split(' ')[1]

		#Save the current course as a session variable.
		session['currentCourse'] = classNoSpace

		conn = mysql.connect()
		cursor = conn.cursor()

		cursor.execute("SELECT courseName,courseOverview from courses where courseAbbreviation=%s", (classNoSpace))
		data = cursor.fetchone()

		return render_template('overview.html', className = classNum, courseTitle = data[0], courseOverview = data[1])

	return redirect(url_for('index'))
