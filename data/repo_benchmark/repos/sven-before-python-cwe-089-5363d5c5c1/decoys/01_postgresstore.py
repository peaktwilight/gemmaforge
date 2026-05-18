    def delete_data(self, session, id):
        self._openContainer(session)
        sid = str(id)
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, str(id))
        query = "DELETE FROM %s WHERE identifier = $1;" % (self.table)
        self._query(query, sid)
        return None
