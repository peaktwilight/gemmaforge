    def on_save(self):
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            f"insert into visitors (ip_address, user_agent, referrer, full_path, visit_time) values ('{self.ip_address}', '{self.user_agent}', '{self.referrer}', '{self.full_path}', '{self.visit_time}');")
        connection.commit()
        connection.close()
        return 0
