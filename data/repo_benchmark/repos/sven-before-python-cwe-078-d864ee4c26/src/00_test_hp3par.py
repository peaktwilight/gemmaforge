    def test_invalid_iscsi_ip(self):
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

        config = self.setup_configuration()
        config.hp3par_iscsi_ips = ['10.10.220.250', '10.10.220.251']
        config.iscsi_ip_address = '10.10.10.10'
        self.mox.ReplayAll()

        # no valid ip addr should be configured.
        self.assertRaises(exception.InvalidInput,
                          self.setup_driver,
                          config,
                          set_up_fakes=False)
