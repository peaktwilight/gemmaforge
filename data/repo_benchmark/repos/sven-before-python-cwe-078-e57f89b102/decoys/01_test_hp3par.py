    def test_create_host(self):
        self.flags(lock_path=self.tempdir)

        #record
        self.clear_mox()
        self.stubs.Set(hpdriver.hpcommon.HP3PARCommon, "get_cpg",
                       self.fake_get_cpg)
        self.stubs.Set(hpdriver.hpcommon.HP3PARCommon, "get_domain",
                       self.fake_get_domain)
        _run_ssh = self.mox.CreateMock(hpdriver.hpcommon.HP3PARCommon._run_ssh)
        self.stubs.Set(hpdriver.hpcommon.HP3PARCommon, "_run_ssh", _run_ssh)

        show_host_cmd = ['showhost', '-verbose', 'fakehost']
        _run_ssh(show_host_cmd, False).AndReturn([pack('no hosts listed'), ''])

        create_host_cmd = (['createhost', '-iscsi', '-persona', '1', '-domain',
                            ('OpenStack',), 'fakehost',
                            'iqn.1993-08.org.debian:01:222'])
        _run_ssh(create_host_cmd, False).AndReturn([CLI_CR, ''])

        _run_ssh(show_host_cmd, False).AndReturn([pack(ISCSI_HOST_RET), ''])
        self.mox.ReplayAll()

        host = self.driver._create_host(self.volume, self.connector)
        self.assertEqual(host['name'], self.FAKE_HOST)
