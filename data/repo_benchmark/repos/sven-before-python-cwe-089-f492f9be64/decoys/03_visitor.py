    def on_save(self):
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "insert into visitors (ip_address, user_agent, referrer, full_path, visit_time) values (%s, %s, %s, %s, %s);",
            (str(self.ip_address), str(self.user_agent), str(self.referrer), str(self.full_path), self.visit_time))
        connection.commit()
        connection.close()
        return 0
