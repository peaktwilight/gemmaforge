    def _delete_host(self, host_name):
        """Delete a host on the storage system."""

        LOG.debug(_('enter: _delete_host: host %s ') % host_name)

        ssh_cmd = 'svctask rmhost %s ' % host_name
        out, err = self._run_ssh(ssh_cmd)
        # No output should be returned from rmhost
        self._assert_ssh_return(len(out.strip()) == 0,
                                '_delete_host', ssh_cmd, out, err)

        LOG.debug(_('leave: _delete_host: host %s ') % host_name)
