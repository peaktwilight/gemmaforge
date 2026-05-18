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
                        ?,
                        ?,
                        ?
                    );
                '''
                self.c.execute(query, (source["serial_id"], 0, source["prev_etotal"]))

                query = '''
                    UPDATE Inverters
                    SET     
                        Name=?, 
                        Type=?, 
                        SW_Version=?, 
                        Status=?,
                        TimeStamp=?
                    WHERE Serial=?;
                '''
                self.c.execute(query, (source["name"], source["inverter_type"], "s0-bridge v0", "OK", int(datetime.now().timestamp()), source["serial_id"] ))

                self.db.commit()
