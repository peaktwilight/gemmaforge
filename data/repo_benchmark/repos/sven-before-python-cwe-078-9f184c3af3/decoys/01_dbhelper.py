    def add_input(self,data):
        connection = self.connect()

        try:
            query = "INSERT INTO crimes (description) VALUES (%s);"
            with connection.cursor() as cursor:
                cursor.execute(query,data)
                connection.commit()
        finally:
            connection.close()
