    def _modify_3par_iscsi_host(self, hostname, iscsi_iqn):
        # when using -add, you can not send the persona or domain options
        command = ['createhost', '-iscsi', '-add', hostname, iscsi_iqn]
        self.common._cli_run(command)
