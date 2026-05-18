    def add_inverters(self):
        interfaces = self.config.get_connection_interfaces()
        for source in interfaces:
            if source["type"] == "inverter":

                query = '''
                    INSERT OR IGNORE INTO Inverters (
                        Serial,
                        EToday,
                        ETotal
                    ) VALUES (
                        %s,
                        %s,
                        %s
                    );
                ''' % (source["serial_id"], 0, source["prev_etotal"])
                self.c.execute(query)

                query = '''
                    UPDATE Inverters
                    SET     
                        Name='%s', 
                        Type='%s', 
                        SW_Version='%s', 
                        Status='%s',
                        TimeStamp='%s'
                    WHERE Serial='%s';
                ''' % (source["name"], source["inverter_type"], "s0-bridge v0", "OK", int(datetime.now().timestamp()), source["serial_id"] )
                self.c.execute(query)

                self.db.commit()
