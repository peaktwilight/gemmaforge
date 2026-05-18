    def delete_resultSet(self, session, id):
        self._openContainer(session)
        sid = str(id)
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, sid)
        query = "DELETE FROM %s WHERE identifier = $1;" % (self.table)
        self._query(query, sid)
