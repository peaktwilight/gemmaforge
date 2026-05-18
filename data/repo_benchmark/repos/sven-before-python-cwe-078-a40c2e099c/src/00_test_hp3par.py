    def test_get_iscsi_ip_active(self):
        self.flags(lock_path=self.tempdir)

        #record set up
        self.clear_mox()
        _run_ssh = self.mox.CreateMock(hpdriver.hpcommon.HP3PARCommon._run_ssh)
        self.stubs.Set(hpdriver.hpcommon.HP3PARCommon, "_run_ssh", _run_ssh)

        show_port_cmd = 'showport'
        _run_ssh(show_port_cmd, False).AndReturn([pack(PORT_RET), ''])

        show_port_i_cmd = 'showport -iscsi'
        _run_ssh(show_port_i_cmd, False).AndReturn([pack(READY_ISCSI_PORT_RET),
                                                    ''])

        show_port_i_cmd = 'showport -iscsiname'
        _run_ssh(show_port_i_cmd, False).AndReturn([pack(SHOW_PORT_ISCSI), ''])

        self.mox.ReplayAll()

        config = self.setup_configuration()
        config.hp3par_iscsi_ips = ['10.10.220.253', '10.10.220.252']
        self.setup_driver(config, set_up_fakes=False)

        #record
        self.clear_mox()
        _run_ssh = self.mox.CreateMock(hpdriver.hpcommon.HP3PARCommon._run_ssh)
        self.stubs.Set(hpdriver.hpcommon.HP3PARCommon, "_run_ssh", _run_ssh)

        show_vlun_cmd = 'showvlun -a -host fakehost'
        _run_ssh(show_vlun_cmd, False).AndReturn([pack(SHOW_VLUN), ''])

        self.mox.ReplayAll()

        ip = self.driver._get_iscsi_ip('fakehost')
        self.assertEqual(ip, '10.10.220.253')
