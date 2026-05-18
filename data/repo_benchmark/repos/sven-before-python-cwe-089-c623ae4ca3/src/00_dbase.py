    def get_roster(self, server_id):
        sql = """SELECT username, role
                 FROM roles
                 WHERE roles.server_id = {0};
                 """.format(server_id)
        self.cur.execute(sql)
        return self.cur.fetchall()
