    def mode_receive(self, request):
        """
        This is called by render_POST when the client is telling us
        that it is ready to receive data as soon as it is available.
        This is the basis of a long-polling (comet) mechanism: the
        server will wait to reply until data is available.

        Args:
            request (Request): Incoming request.

        """
        csessid = cgi.escape(request.args['csessid'][0])
        self.last_alive[csessid] = (time.time(), False)

        dataentries = self.databuffer.get(csessid, [])
        if dataentries:
            return dataentries.pop(0)
        request.notifyFinish().addErrback(self._responseFailed, csessid, request)
        if csessid in self.requests:
            self.requests[csessid].finish()  # Clear any stale request.
        self.requests[csessid] = request
        return server.NOT_DONE_YET
