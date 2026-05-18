    def verify_email(self, member):
        self.cursor.execute("SELECT COUNT(email) FROM members WHERE email = ':email'", {'email':member})
        result = self.cursor.fetchone()
        if (int(result[0]) > 0):
            return True 
        else:
            return False
