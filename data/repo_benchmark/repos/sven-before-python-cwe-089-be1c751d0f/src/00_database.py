    def get_requested_month_for_inverter(self, inverter_serial, date):
        data = dict()

        month_start, month_end = self.get_epoch_month(date)
        data['interval'] = {'from': self.convert_local_ts_to_utc(month_start, self.local_timezone), 'to': self.convert_local_ts_to_utc(month_end, self.local_timezone)}
        month_total = 0

        query = '''
            SELECT TimeStamp, DayYield AS Power 
            FROM MonthData 
            WHERE TimeStamp BETWEEN %s AND %s AND Serial = %s
            '''

        data['data'] = list()
        for row in self.c.execute(query % (month_start, month_end, inverter_serial)):
            data['data'].append({'time': self.convert_local_ts_to_utc(row[0], self.local_timezone), 'power': row[1]})
            month_total += row[1]

        data['total'] = month_total

        query = '''
            SELECT MIN(TimeStamp) as Min, MAX(TimeStamp) as Max 
            FROM MonthData 
            WHERE Serial = %s;
            ''' % inverter_serial

        self.c.execute(query)
        first_data, last_data = self.c.fetchone()

        if first_data: data['hasPrevious'] = (first_data < month_start)
        else: data['hasPrevious'] = False
        if last_data: data['hasNext'] = (last_data > month_end)
        else: data['hasNext'] = False

        return data
