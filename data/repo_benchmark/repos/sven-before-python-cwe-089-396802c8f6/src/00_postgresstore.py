    def store_metadata(self, session, key, mType, value):
        if (self.idNormalizer is not None):
            id = self.idNormalizer.process_string(session, id)
        elif type(id) == unicode:
            id = id.encode('utf-8')
        else:
            id = str(id)
        self._openContainer(session)
        query = ("UPDATE %s SET %s = %r WHERE identifier = '%s';" %
                 (self.table, mType, value, id)
                 )
        try:
            self._query(query)
        except:
            return None
        return value
