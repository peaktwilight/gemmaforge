    def mode_keepalive(self, request):
        """
        This is called by render_POST when the
        client is replying to the keepalive.
        """
        csessid = cgi.escape(request.args['csessid'][0])
        self.last_alive[csessid] = (time.time(), False)
        return '""'
