    def get(self, space_id):
        """ Fetch data for space with the corresponding space_id """
        return database_utilities.execute_query(
            f"""select * from spaces where space_id = %s""", (space_id, ))
