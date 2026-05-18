@app.route('/delete_video/<filename>')
def delete_video(filename):
	if 'username' in session:
		#os.remove("static/videos/{}".format(filename))
		print(session['username'], file=sys.stdout)
		data=users.query.filter_by(Username=session['username']).first()
		video=Video.query.filter_by(UserID=data.UserID,Name=filename).first()
		if video != None:
			#os.remove("static/videos/{}".format(filename))
			os.system("rm static/videos/{}".format(filename))
			db.session.delete(video)
			db.session.commit()
		else:
			return "Don't delete other people's videos!"
		return redirect(url_for('upload'))
	return "test"
