    def mode_input(self, request):
        """
        This is called by render_POST when the client
        is sending data to the server.

        Args:
            request (Request): Incoming request.

        """
        csessid = cgi.escape(request.args['csessid'][0])
        self.last_alive[csessid] = (time.time(), False)
        sess = self.sessionhandler.sessions_from_csessid(csessid)
        if sess:
            sess = sess[0]
            cmdarray = json.loads(cgi.escape(request.args.get('data')[0]))
            sess.sessionhandler.data_in(sess, **{cmdarray[0]: [cmdarray[1], cmdarray[2]]})
        return '""'
