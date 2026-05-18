    def _get_host_from_connector(self, connector):
        """List the hosts defined in the storage.

        Return the host name with the given connection info, or None if there
        is no host fitting that information.

        """

        prefix = self._connector_to_hostname_prefix(connector)
        LOG.debug(_('enter: _get_host_from_connector: prefix %s') % prefix)

        # Get list of host in the storage
        ssh_cmd = 'svcinfo lshost -delim !'
        out, err = self._run_ssh(ssh_cmd)

        if not len(out.strip()):
            return None

        # If we have FC information, we have a faster lookup option
        hostname = None
        if 'wwpns' in connector:
            hostname = self._find_host_from_wwpn(connector)

        # If we don't have a hostname yet, try the long way
        if not hostname:
            host_lines = out.strip().split('\n')
            self._assert_ssh_return(len(host_lines),
                                    '_get_host_from_connector',
                                    ssh_cmd, out, err)
            header = host_lines.pop(0).split('!')
            self._assert_ssh_return('name' in header,
                                    '_get_host_from_connector',
                                    ssh_cmd, out, err)
            name_index = header.index('name')
            hosts = map(lambda x: x.split('!')[name_index], host_lines)
            hostname = self._find_host_exhaustive(connector, hosts)

        LOG.debug(_('leave: _get_host_from_connector: host %s') % hostname)

        return hostname
