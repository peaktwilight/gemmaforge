    def mode_close(self, request):
        """
        This is called by render_POST when the client is signalling
        that it is about to be closed.

        Args:
            request (Request): Incoming request.

        """
        csessid = cgi.escape(request.args['csessid'][0])
        try:
            sess = self.sessionhandler.sessions_from_csessid(csessid)[0]
            sess.sessionhandler.disconnect(sess)
        except IndexError:
            self.client_disconnect(csessid)
        return '""'
