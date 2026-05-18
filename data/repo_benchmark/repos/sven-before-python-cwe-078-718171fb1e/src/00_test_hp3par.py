    def test_create_invalid_host(self):
        self.flags(lock_path=self.tempdir)

        #record
        self.clear_mox()
        self.stubs.Set(hpdriver.hpcommon.HP3PARCommon, "get_cpg",
                       self.fake_get_cpg)
        self.stubs.Set(hpdriver.hpcommon.HP3PARCommon, "get_domain",
                       self.fake_get_domain)
        _run_ssh = self.mox.CreateMock(hpdriver.hpcommon.HP3PARCommon._run_ssh)
        self.stubs.Set(hpdriver.hpcommon.HP3PARCommon, "_run_ssh", _run_ssh)

        show_host_cmd = 'showhost -verbose fakehost'
        _run_ssh(show_host_cmd, False).AndReturn([pack('no hosts listed'), ''])

        create_host_cmd = ('createhost -persona 1 -domain (\'OpenStack\',) '
                           'fakehost 123456789012345 123456789054321')
        create_host_ret = pack(CLI_CR +
                               'already used by host fakehost.foo (19)')
        _run_ssh(create_host_cmd, False).AndReturn([create_host_ret, ''])

        show_3par_cmd = 'showhost -verbose fakehost.foo'
        _run_ssh(show_3par_cmd, False).AndReturn([pack(FC_SHOWHOST_RET), ''])
        self.mox.ReplayAll()

        host = self.driver._create_host(self.volume, self.connector)

        self.assertEquals(host['name'], 'fakehost.foo')
