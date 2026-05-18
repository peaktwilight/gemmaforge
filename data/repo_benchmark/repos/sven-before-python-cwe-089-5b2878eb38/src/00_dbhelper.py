    def add_input(self,data):
        connection = self.connect()
        try:
            # The following is a flaw
            query = "INSERT INTO crimes(description) VALUES ('{}');".format(data)
            with connection.cursor() as cursor:
                cursor.execute(query)
                connection.commit()
        finally:
            connection.close()
