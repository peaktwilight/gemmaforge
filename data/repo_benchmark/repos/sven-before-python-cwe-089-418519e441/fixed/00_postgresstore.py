    def fetch_data(self, session, id):
        self._openContainer(session)
        sid = str(id)
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, sid)
        query = ("SELECT data FROM %s WHERE identifier = $1;" %
                 (self.table)
                 )
        res = self._query(query, sid)
        try:
            data = res.dictresult()[0]['data']
        except IndexError:
            raise ObjectDoesNotExistException(id)
        try:
            ndata = pg.unescape_bytea(data)
        except:
            # insufficient PyGreSQL version
            ndata = data.replace("\\'", "'")

        ndata = ndata.replace('\\000\\001', nonTextToken)
        ndata = ndata.replace('\\012', '\n')
        return ndata
