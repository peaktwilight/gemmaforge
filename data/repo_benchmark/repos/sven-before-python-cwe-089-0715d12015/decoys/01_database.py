    def get_previous_yields(self, inverter_serial):
        query = '''
           SELECT TimeStamp, EToday, ETotal
           FROM Inverters
           WHERE Serial=?
        '''
        self.c.execute(query, (inverter_serial,))
        data = self.c.fetchone()
        return data[0], data[1], data[2]
