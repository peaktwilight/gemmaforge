@app.route('/api/uploads/<sid>/logs')
def get_logs(sid):
    if utils.sid_is_valid(sid):
        path = join(app.config['UPLOAD_FOLDER'], sid)

        if os.path.isfile(join(path, app.config['LOG_FILE'])):
            return send_from_directory(directory=path,
                                        filename=app.config['LOG_FILE'])
        else:
            abort(404)
    else:
        abort(404)
