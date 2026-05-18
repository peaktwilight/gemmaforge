    def add_consumption_data_row(self, ts, energy_used, power_used):

        if power_used > 0:

            query = '''
                INSERT OR IGNORE INTO Consumption (
                    TimeStamp,
                    EnergyUsed,
                    PowerUsed                                
                ) VALUES (
                    %s,
                    %s,
                    %s
                );
            ''' % (ts, 0, 0)
            self.c.execute(query)

            query = '''
                UPDATE Consumption SET 
                EnergyUsed = EnergyUsed + %s,
                PowerUsed = PowerUsed + %s
                WHERE TimeStamp = %s;
            ''' % (energy_used, power_used, ts)

            self.c.execute(query)

            self.db.commit()
