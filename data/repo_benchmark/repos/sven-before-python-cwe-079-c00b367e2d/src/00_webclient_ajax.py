    def mode_keepalive(self, request):
        """
        This is called by render_POST when the
        client is replying to the keepalive.
        """
        csessid = request.args.get('csessid')[0]
        self.last_alive[csessid] = (time.time(), False)
        return '""'
