    def test_get_least_used_nsp(self):
        self.flags(lock_path=self.tempdir)

        #record
        self.clear_mox()
        _run_ssh = self.mox.CreateMock(hpdriver.hpcommon.HP3PARCommon._run_ssh)
        self.stubs.Set(hpdriver.hpcommon.HP3PARCommon, "_run_ssh", _run_ssh)

        show_vlun_cmd = 'showvlun -a -showcols Port'
        _run_ssh(show_vlun_cmd, False).AndReturn([pack(SHOW_VLUN_NONE), ''])
        _run_ssh(show_vlun_cmd, False).AndReturn([pack(SHOW_VLUN_NONE), ''])
        _run_ssh(show_vlun_cmd, False).AndReturn([pack(SHOW_VLUN_NONE), ''])

        self.mox.ReplayAll()
        # in use count                           11       12
        nsp = self.driver._get_least_used_nsp(['0:2:1', '1:8:1'])
        self.assertEqual(nsp, '0:2:1')

        # in use count                            11       10
        nsp = self.driver._get_least_used_nsp(['0:2:1', '1:2:1'])
        self.assertEqual(nsp, '1:2:1')

        # in use count                            0       10
        nsp = self.driver._get_least_used_nsp(['1:1:1', '1:2:1'])
        self.assertEqual(nsp, '1:1:1')
