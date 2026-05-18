    def check_if_this_project_is_in_database(self, project_id):
        self.cursor.execute("SELECT count(id) FROM projects where id = %s", (project_id,))
        return self.cursor.fetchall()[0][0] == 1
