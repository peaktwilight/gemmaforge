    def is_cgi(self):
        """Test whether self.path corresponds to a CGI script.

        Returns True and updates the cgi_info attribute to the tuple
        (dir, rest) if self.path requires running a CGI script.
        Returns False otherwise.

        The default implementation tests whether the normalized url
        path begins with one of the strings in self.cgi_directories
        (and the next character is a '/' or the end of the string).
        """
        splitpath = _url_collapse_path_split(self.path)
        if splitpath[0] in self.cgi_directories:
            self.cgi_info = splitpath
            return True
        return False
