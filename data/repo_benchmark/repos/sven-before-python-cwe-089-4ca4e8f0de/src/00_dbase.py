    def create_event(self, title, start_time, time_zone, server_id, description):
        sql = """INSERT INTO events (title, start_time, time_zone, server_id, description)
                 VALUES ('{0}', '{1}', '{2}', '{3}', '{4}')
                 """.format(title, start_time, time_zone, server_id, description)
        self.cur.execute(sql)
        self.conn.commit()
