    def mode_init(self, request):
        """
        This is called by render_POST when the client requests an init
        mode operation (at startup)

        Args:
            request (Request): Incoming request.

        """
        csessid = cgi.escape(request.args['csessid'][0])

        remote_addr = request.getClientIP()
        host_string = "%s (%s:%s)" % (_SERVERNAME, request.getRequestHostname(), request.getHost().port)

        sess = AjaxWebClientSession()
        sess.client = self
        sess.init_session("ajax/comet", remote_addr, self.sessionhandler)

        sess.csessid = csessid
        csession = _CLIENT_SESSIONS(session_key=sess.csessid)
        uid = csession and csession.get("webclient_authenticated_uid", False)
        if uid:
            # the client session is already logged in
            sess.uid = uid
            sess.logged_in = True

        sess.sessionhandler.connect(sess)

        self.last_alive[csessid] = (time.time(), False)
        if not self.keep_alive:
            # the keepalive is not running; start it.
            self.keep_alive = LoopingCall(self._keepalive)
            self.keep_alive.start(_KEEPALIVE, now=False)

        return jsonify({'msg': host_string, 'csessid': csessid})
