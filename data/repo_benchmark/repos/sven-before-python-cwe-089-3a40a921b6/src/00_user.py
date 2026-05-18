    def user_verify(self):
        eid = self.email
        code = self.password
        if eid.strip() == '':
            return
        if code.strip() == '':
            return
        query = '''select * from usr where email like\''''+eid+'\''
        cursor = g.conn.execute(query)
        for row in cursor:
            key = str(row.password)
            if key.strip() == code.strip():
                self.name = str(row.name)
                self.email = eid
                self.id = eid
                self.valid = True
            break
