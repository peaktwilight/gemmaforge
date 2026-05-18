    def all_deposits(self,coin):
        sql = "SELECT * FROM deposits WHERE coin='%s'" % coin
        self.cursor.execute(sql)
        return self.cursor.fetchall()
