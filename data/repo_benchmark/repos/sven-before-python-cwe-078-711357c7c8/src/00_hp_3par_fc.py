    def _modify_3par_fibrechan_host(self, hostname, wwn):
        # when using -add, you can not send the persona or domain options
        out = self.common._cli_run('createhost -add %s %s'
                                   % (hostname, " ".join(wwn)), None)
