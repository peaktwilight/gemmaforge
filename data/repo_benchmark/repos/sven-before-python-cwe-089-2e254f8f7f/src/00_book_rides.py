    def verify_rno(self, rno):
        query = "SELECT COUNT(rno) FROM rides WHERE rno = {rno}".format(rno = rno)
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        if (int(result[0]) > 0):
            return True 
        else:
            return False
