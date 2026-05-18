    def _delete_3par_host(self, hostname):
        self._cli_run('removehost %s' % hostname, None)
