    def update_inverter(self, inverter_serial, ts, status, etoday, etotal):
        query = '''
            UPDATE Inverters
            SET     
                TimeStamp=?, 
                Status=?, 
                eToday=?,
                eTotal=?
            WHERE Serial=?;
        '''
        self.c.execute(query, (ts, status, etoday, etotal, inverter_serial))
