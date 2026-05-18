    def _modify_3par_fibrechan_host(self, hostname, wwns):
        # when using -add, you can not send the persona or domain options
        command = ['createhost', '-add', hostname]
        for wwn in wwns:
            command.append(wwn)

        out = self.common._cli_run(command)
