    def canonicalize(self):
        """::

            path = path.canonicalize()

        Canonicalize path. ::

            # "/foo/baz"
            Pyjo.Path.new('/foo/./bar/../baz').canonicalize()

            # "/../baz"
            Pyjo.Path.new('/foo/../bar/../../baz').canonicalize()
        """
        parts = self.parts
        i = 0
        while i < len(parts):
            if parts[i] == '.' or parts[i] == '':
                parts.pop(i)
            elif i < 1 or parts[i] != '..' or parts[i - 1] == '..':
                i += 1
            else:
                i -= 1
                parts.pop(i)
                parts.pop(i)

        if not parts:
            self.trailing_slash = False

        return self
