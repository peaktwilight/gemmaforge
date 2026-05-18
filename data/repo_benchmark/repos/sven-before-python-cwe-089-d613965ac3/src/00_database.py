    def update_inverter(self, inverter_serial, ts, status, etoday, etotal):
        query = '''
            UPDATE Inverters
            SET     
                TimeStamp='%s', 
                Status='%s', 
                eToday='%s',
                eTotal='%s'
            WHERE Serial='%s';
        ''' % (ts, status, etoday, etotal, inverter_serial)
        self.c.execute(query)
