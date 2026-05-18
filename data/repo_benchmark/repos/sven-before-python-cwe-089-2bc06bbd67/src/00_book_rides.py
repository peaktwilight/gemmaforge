    def verify_email(self, member):
        query = "SELECT COUNT(email) FROM members WHERE email = '{email}'".format(email = member)
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        if (int(result[0]) > 0):
            return True 
        else:
            return False
