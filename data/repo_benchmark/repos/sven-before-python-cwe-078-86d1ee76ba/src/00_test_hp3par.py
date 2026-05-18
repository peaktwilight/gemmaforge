    def test_get_iscsi_ip(self):
        self.flags(lock_path=self.tempdir)

        #record driver set up
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

        #record
        show_vlun_cmd = 'showvlun -a -host fakehost'
        show_vlun_ret = 'no vluns listed\r\n'
        _run_ssh(show_vlun_cmd, False).AndReturn([pack(show_vlun_ret), ''])
        show_vlun_cmd = 'showvlun -a -showcols Port'
        _run_ssh(show_vlun_cmd, False).AndReturn([pack(SHOW_VLUN_NONE), ''])

        self.mox.ReplayAll()

        config = self.setup_configuration()
        config.iscsi_ip_address = '10.10.10.10'
        config.hp3par_iscsi_ips = ['10.10.220.253', '10.10.220.252']
        self.setup_driver(config, set_up_fakes=False)

        ip = self.driver._get_iscsi_ip('fakehost')
        self.assertEqual(ip, '10.10.220.252')
