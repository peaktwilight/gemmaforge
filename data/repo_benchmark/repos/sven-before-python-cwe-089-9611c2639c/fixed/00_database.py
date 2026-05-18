    def add_month_data_row(self, inverter_serial, ts, etoday, etotal):

        y = datetime.fromtimestamp(ts) - timedelta(days=1)
        y_ts = int(datetime(y.year, y.month, y.day, 23, tzinfo=pytz.utc).timestamp())

        query = '''
            INSERT INTO MonthData (
                TimeStamp,
                Serial,
                DayYield,
                TotalYield                                 
            ) VALUES (
                ?,
                ?,
                ?,
                ?
            );
        '''
        self.c.execute(query, (y_ts, inverter_serial, etoday, etotal))
