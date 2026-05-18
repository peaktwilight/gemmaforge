    def delete_event(self, event_id):
        sql = """
              DELETE FROM events
              WHERE event_id = %s
              """
        affected_count = self.cur.execute(sql, (event_id,))
        self.conn.commit()
        return affected_count
