    def test_initialize_connection(self):
        self.driver._eql_execute = self.mox.\
            CreateMock(self.driver._eql_execute)
        volume = {'name': self.volume_name}
        self.stubs.Set(self.driver, "_get_iscsi_properties",
                       self._fake_get_iscsi_properties)
        self.driver._eql_execute('volume', 'select', volume['name'], 'access',
                                 'create', 'initiator',
                                 self.connector['initiator'],
                                 'authmethod', 'chap',
                                 'username',
                                 self.configuration.eqlx_chap_login)
        self.mox.ReplayAll()
        iscsi_properties = self.driver.initialize_connection(volume,
                                                             self.connector)
        self.assertEqual(iscsi_properties['data'],
                         self._fake_get_iscsi_properties(volume))
