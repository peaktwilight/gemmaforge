    def add_day_data_row(self, ts, data, prev_etotal):

        if data['power'] > 0:

            inv_serial = data['source']['serial_id']
            query = '''
               INSERT INTO DayData (
                   TimeStamp,
                   Serial,
                   Power,
                   TotalYield
               ) VALUES (
                   ?,
                   ?,
                   ?,
                   ?
               );
            '''
            self.c.execute(query, (ts, inv_serial, data['power'],  prev_etotal + data['energy']))
