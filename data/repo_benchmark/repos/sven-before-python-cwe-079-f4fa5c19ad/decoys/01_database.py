    def get_requested_day(self, date):

        data = dict()

        day_start, day_end = self.get_epoch_day(date)
        data['interval'] = {'from': self.convert_local_ts_to_utc(day_start, self.local_timezone), 'to': self.convert_local_ts_to_utc(day_end, self.local_timezone)}

        query = '''
            SELECT TimeStamp, SUM(Power) AS Power 
            FROM DayData 
            WHERE TimeStamp BETWEEN ? AND ?
            GROUP BY TimeStamp;
        '''

        data['data'] = list()
        for row in self.c.execute(query, (day_start, day_end)):
            data['data'].append({ 'time': row[0], 'power': row[1] })


        if self.get_datetime(date).date() == datetime.today().date():
            query = '''
                SELECT SUM(EToday) as EToday
                FROM Inverters;
                '''
            self.c.execute(query)
        else:
            query = '''
                SELECT SUM(DayYield) AS Power 
                FROM MonthData 
                WHERE TimeStamp BETWEEN ? AND ?
                GROUP BY TimeStamp;
                '''
            self.c.execute(query, (day_start, day_end))

        row = self.c.fetchone()
        if row and row[0]: data['total'] = row[0]
        else: data['total'] = 0


        query = '''
            SELECT MIN(TimeStamp) as Min, MAX(TimeStamp) as Max 
            FROM ( SELECT TimeStamp FROM DayData GROUP BY TimeStamp );
            '''

        self.c.execute(query)
        first_data, last_data = self.c.fetchone()

        if (first_data):  data['hasPrevious'] = (first_data < day_start)
        else: data['hasPrevious'] = False

        if (last_data): data['hasNext'] = (last_data > day_end)
        else: data['hasNext'] = False

        #print(json.dumps(data, indent=4))
        return data
