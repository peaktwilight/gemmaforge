    def delete_data(self, session, id):
        self._openContainer(session)
        sid = str(id)
        if (self.idNormalizer is not None):
            sid = self.idNormalizer.process_string(session, str(id))
        query = "DELETE FROM %s WHERE identifier = '%s';" % (self.table, sid)
        self._query(query)
        return None
