    def writeToDb(self, url):
        try:
            self.cursor.execute("INSERT INTO queue (url, visited) VALUES ('{}', '0');".format(url))
            self.db.commit()
        except Exception as e:
            print(e)
