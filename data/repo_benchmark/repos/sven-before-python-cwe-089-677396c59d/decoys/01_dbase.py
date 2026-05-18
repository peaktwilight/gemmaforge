    def get_roster(self, server_id):
        sql = """
              SELECT username, role
              FROM roles
              WHERE roles.server_id = %s;
              """
        self.cur.execute(sql, (server_id,))
        return self.cur.fetchall()
