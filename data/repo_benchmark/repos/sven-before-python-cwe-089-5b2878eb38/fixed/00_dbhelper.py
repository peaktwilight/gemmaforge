    def add_input(self, data):
        connection = self.connect()
        try:
            # The following introduces a deliberate security flaw. 
            # See section on SQL injection below
            query = "INSERT INTO crimes (description) VALUES(%s);"
            with connection.cursor() as cursor:
                cursor.execute(query, data)
                connection.commit()
        finally:
            connection.close()
