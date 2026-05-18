    def mode_input(self, request):
        """
        This is called by render_POST when the client
        is sending data to the server.

        Args:
            request (Request): Incoming request.

        """
        csessid = request.args.get('csessid')[0]

        self.last_alive[csessid] = (time.time(), False)
        sess = self.sessionhandler.sessions_from_csessid(csessid)
        if sess:
            sess = sess[0]
            cmdarray = json.loads(request.args.get('data')[0])
            sess.sessionhandler.data_in(sess, **{cmdarray[0]: [cmdarray[1], cmdarray[2]]})
        return '""'
