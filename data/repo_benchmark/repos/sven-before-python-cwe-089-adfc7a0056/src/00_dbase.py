    def delete_event(self, event_id):
        sql = """DELETE FROM events
                 WHERE event_id = {0}
                 """.format(event_id)
        affected_count = self.cur.execute(sql)
        self.conn.commit()
        return affected_count
