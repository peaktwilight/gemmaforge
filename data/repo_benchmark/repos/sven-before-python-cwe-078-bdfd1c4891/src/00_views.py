@app.route('/api/uploads/<sid>/logs')
def get_logs(sid):
    if '/' not in sid:
        path = os.path.join(app.config['UPLOAD_FOLDER'], sid)
        if os.path.isfile(os.path.join(path, app.config['LOG_FILE'])):
            return send_from_directory(directory=path,
                                        filename=app.config['LOG_FILE'])
        else:
            abort(404)
    else:
        abort(403)
