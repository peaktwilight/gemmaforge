    def is_cgi(self):
        """Test whether self.path corresponds to a CGI script,
        and return a boolean.

        This function sets self.cgi_info to a tuple (dir, rest)
        when it returns True, where dir is the directory part before
        the CGI script name.  Note that rest begins with a
        slash if it is not empty.

        The default implementation tests whether the path
        begins with one of the strings in the list
        self.cgi_directories (and the next character is a '/'
        or the end of the string).
        """

        path = self.path

        for x in self.cgi_directories:
            i = len(x)
            if path[:i] == x and (not path[i:] or path[i] == '/'):
                self.cgi_info = path[:i], path[i+1:]
                return True
        return False
