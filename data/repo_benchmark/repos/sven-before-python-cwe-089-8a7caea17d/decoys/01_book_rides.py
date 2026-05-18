    def verify_rno(self, rno):
        self.cursor.execute("SELECT COUNT(rno) FROM rides WHERE rno = :rno", {'rno': rno})
        result = self.cursor.fetchone()
        if (int(result[0]) > 0):
            return True 
        else:
            return False
