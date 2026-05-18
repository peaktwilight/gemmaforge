    def getQueue(self, numberOfLinks=10):
        self.cursor.execute("SELECT url FROM queue WHERE visited = '0' LIMIT {};".format(numberOfLinks))
        result = self.cursor.fetchall()
        self.remove(result)
        return result
