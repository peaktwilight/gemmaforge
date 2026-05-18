    def get_user(self):
        if not hasattr(self, '_user'):
            qs = "select * from account_access where access_token = '%s'" % self.access_token
            result = self.db.get(qs)
            if result:
                self._user = result
            else:
                self._user = None
        
        return self._user
