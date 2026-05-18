    def get_previous_yields(self, inverter_serial):
        query = '''
           SELECT TimeStamp, EToday, ETotal
           FROM Inverters
           WHERE Serial = '%s'
        ''' % (inverter_serial)
        self.c.execute(query)
        data = self.c.fetchone()
        return data[0], data[1], data[2]
