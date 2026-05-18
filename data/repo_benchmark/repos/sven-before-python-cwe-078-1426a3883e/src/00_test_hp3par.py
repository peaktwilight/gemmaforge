    def test_get_ports(self):
        self.flags(lock_path=self.tempdir)

        #record
        self.clear_mox()
        _run_ssh = self.mox.CreateMock(hpdriver.hpcommon.HP3PARCommon._run_ssh)
        self.stubs.Set(hpdriver.hpcommon.HP3PARCommon, "_run_ssh", _run_ssh)

        show_port_cmd = 'showport'
        _run_ssh(show_port_cmd, False).AndReturn([pack(PORT_RET), ''])

        show_port_i_cmd = 'showport -iscsi'
        _run_ssh(show_port_i_cmd, False).AndReturn([pack(READY_ISCSI_PORT_RET),
                                                    ''])

        show_port_i_cmd = 'showport -iscsiname'
        _run_ssh(show_port_i_cmd, False).AndReturn([pack(SHOW_PORT_ISCSI),
                                                    ''])
        self.mox.ReplayAll()

        ports = self.driver.common.get_ports()
        self.assertEqual(ports['FC'][0], '20210002AC00383D')
        self.assertEqual(ports['iSCSI']['10.10.120.252']['nsp'], '0:8:2')
