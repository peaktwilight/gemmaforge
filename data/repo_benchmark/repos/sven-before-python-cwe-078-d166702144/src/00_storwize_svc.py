    def _get_chap_secret_for_host(self, host_name):
        """Return the CHAP secret for the given host."""

        LOG.debug(_('enter: _get_chap_secret_for_host: host name %s')
                  % host_name)

        ssh_cmd = 'svcinfo lsiscsiauth -delim !'
        out, err = self._run_ssh(ssh_cmd)

        if not len(out.strip()):
            return None

        host_lines = out.strip().split('\n')
        self._assert_ssh_return(len(host_lines), '_get_chap_secret_for_host',
                                ssh_cmd, out, err)

        header = host_lines.pop(0).split('!')
        self._assert_ssh_return('name' in header, '_get_chap_secret_for_host',
                                ssh_cmd, out, err)
        self._assert_ssh_return('iscsi_auth_method' in header,
                                '_get_chap_secret_for_host', ssh_cmd, out, err)
        self._assert_ssh_return('iscsi_chap_secret' in header,
                                '_get_chap_secret_for_host', ssh_cmd, out, err)
        name_index = header.index('name')
        method_index = header.index('iscsi_auth_method')
        secret_index = header.index('iscsi_chap_secret')

        chap_secret = None
        host_found = False
        for line in host_lines:
            info = line.split('!')
            if info[name_index] == host_name:
                host_found = True
                if info[method_index] == 'chap':
                    chap_secret = info[secret_index]

        self._assert_ssh_return(host_found, '_get_chap_secret_for_host',
                                ssh_cmd, out, err)

        LOG.debug(_('leave: _get_chap_secret_for_host: host name '
                    '%(host_name)s with secret %(chap_secret)s')
                  % {'host_name': host_name, 'chap_secret': chap_secret})

        return chap_secret
