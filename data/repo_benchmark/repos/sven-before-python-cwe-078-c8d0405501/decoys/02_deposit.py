    def all_deposits(self,coin):
        sql = "SELECT * FROM deposits WHERE coin='%s'"
        self.cursor.execute(sql, (coin,))
        return self.cursor.fetchall()
