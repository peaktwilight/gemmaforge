    def fetch_resultSet(self, session, id):
        self._openContainer(session)

        sid = str(id)
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, sid)
        query = ("SELECT class, data FROM %s WHERE identifier = '%s';" %
                 (self.table, sid)
                 )
        res = self._query(query)
        try:
            rdict = res.dictresult()[0]
        except IndexError:
            raise ObjectDoesNotExistException('%s/%s' % (self.id, sid))

        data = rdict['data']
        try:
            ndata = pg.unescape_bytea(data)
        except:
            # Insufficient PyGreSQL version
            ndata = data.replace("\\'", "'")

        ndata = ndata.replace('\\000', '\x00')
        ndata = ndata.replace('\\012', '\n')
        # data is res.dictresult()
        cl = rdict['class']
        rset = dynamic.buildObject(session, cl, [[]])
        rset.deserialize(session, ndata)
        rset.id = id

        # Update expires
        now = time.time()
        nowStr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now))
        expires = now + self.get_default(session, 'expires', 600)
        rset.timeExpires = expires
        expiresStr = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(expires))

        query = ("UPDATE %s SET timeAccessed = '%s', expires = '%s' "
                 "WHERE identifier = '%s';" %
                 (self.table, nowStr, expiresStr, sid)
                 )
        self._query(query)
        return rset
