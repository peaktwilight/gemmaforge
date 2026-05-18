    def add_consumption_data_row(self, ts, energy_used, power_used):

        if power_used > 0:

            query = '''
                INSERT OR IGNORE INTO Consumption (
                    TimeStamp,
                    EnergyUsed,
                    PowerUsed                                
                ) VALUES (
                    ?,
                    ?,
                    ?
                );
            '''
            self.c.execute(query, (ts, 0, 0))

            query = '''
                UPDATE Consumption SET 
                EnergyUsed = EnergyUsed + ?,
                PowerUsed = PowerUsed + ?
                WHERE TimeStamp=?;
            '''

            self.c.execute(query, (energy_used, power_used, ts))

            self.db.commit()
