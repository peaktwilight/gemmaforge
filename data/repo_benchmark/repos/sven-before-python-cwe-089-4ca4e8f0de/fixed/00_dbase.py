    def create_event(self, title, start_time, time_zone, server_id, description):
        sql = """
              INSERT INTO events (title, start_time, time_zone, server_id, description)
              VALUES (%s, %s, %s, %s, %s)
              """
        self.cur.execute(sql, (title, start_time, time_zone, server_id, description))
        self.conn.commit()
