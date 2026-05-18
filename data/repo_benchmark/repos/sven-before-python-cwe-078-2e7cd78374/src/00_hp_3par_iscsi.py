    def _modify_3par_iscsi_host(self, hostname, iscsi_iqn):
        # when using -add, you can not send the persona or domain options
        self.common._cli_run('createhost -iscsi -add %s %s'
                             % (hostname, iscsi_iqn), None)
