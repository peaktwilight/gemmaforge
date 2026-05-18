    def handle(self, keepalive=True, initial_timeout=None):
        # we are requested to skip processing and keep the previous values
        if self.skip:
            return self.response.handle()

        # default to no keepalive in case something happens while even trying ensure we have a request
        self.keepalive = False

        self.headers = HTTPHeaders()

        # if initial_timeout is set, only wait that long for the initial request line
        if initial_timeout:
            self.connection.settimeout(initial_timeout)
        else:
            self.connection.settimeout(self.timeout)

        # get request line
        try:
            # ignore empty lines waiting on request
            request = '\r\n'
            while request == '\r\n':
                request = self.rfile.readline(max_line_size + 1).decode(http_encoding)
        # if read hits timeout or has some other error, ignore the request
        except Exception:
            return True

        # ignore empty requests
        if not request:
            return True

        # we have a request, go back to normal timeout
        if initial_timeout:
            self.connection.settimeout(self.timeout)

        # remove \r\n from the end
        self.request_line = request[:-2]

        # set some reasonable defaults in case the worst happens and we need to tell the client
        self.method = ''
        self.resource = '/'

        try:
            # HTTP Status 414
            if len(request) > max_line_size:
                raise HTTPError(414)

            # HTTP Status 400
            if request[-2:] != '\r\n':
                raise HTTPError(400)

            # try the request line and error out if can't parse it
            try:
                self.method, self.resource, self.request_http = self.request_line.split()
            # HTTP Status 400
            except ValueError:
                raise HTTPError(400)

            # HTTP Status 505
            if self.request_http != http_version:
                raise HTTPError(505)

            # read and parse request headers
            while True:
                line = self.rfile.readline(max_line_size + 1).decode(http_encoding)

                # hit end of headers
                if line == '\r\n':
                    break

                self.headers.add(line)

            # if we are requested to close the connection after we finish, do so
            if self.headers.get('Connection') == 'close':
                self.keepalive = False
            # else since we are sure we have a request and have read all of the request data, keepalive for more later (if allowed)
            else:
                self.keepalive = keepalive

            # find a matching regex to handle the request with
            for regex, handler in self.server.routes.items():
                match = regex.match(self.resource)
                if match:
                    # create a dictionary of groups
                    groups = match.groupdict()
                    values = groups.values()

                    for idx, group in enumerate(match.groups()):
                        if group not in values:
                            groups[idx] = group

                    # create handler
                    self.handler = handler(self, self.response, groups)
                    break
            # HTTP Status 404
            # if loop is not broken (handler is not found), raise a 404
            else:
                raise HTTPError(404)
        # use DummyHandler so the error is raised again when ready for response
        except Exception as error:
            self.handler = DummyHandler(self, self.response, (), error)
        finally:
            # we finished listening and handling early errors and so let a response class now finish up the job of talking
            return self.response.handle()
