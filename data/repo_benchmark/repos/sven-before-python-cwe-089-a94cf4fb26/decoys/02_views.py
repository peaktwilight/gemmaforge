@app.route('/view/<sid>')
def view(sid):
    if utils.sid_is_valid(sid):
        path = join(app.config['UPLOAD_FOLDER'], sid)
        if os.path.isdir(path):
            using_firebase = 'true' if app.config['FIREBASE'] else 'false'
            return render_template('view.html', sid=sid,
                                    title="Progress for %s" % sid,
                                    using_firebase=using_firebase)
        else:
            abort(404)
    else:
        abort(403)
