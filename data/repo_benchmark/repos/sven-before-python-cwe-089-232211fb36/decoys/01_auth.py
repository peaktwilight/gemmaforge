    def get_user(self):
        if not hasattr(self, '_user'):
            qs = "select * from account_access where access_token = %s"
            result = self.db.get(qs, self.access_token)
            if result:
                self._user = result
            else:
                self._user = None
        
        return self._user
