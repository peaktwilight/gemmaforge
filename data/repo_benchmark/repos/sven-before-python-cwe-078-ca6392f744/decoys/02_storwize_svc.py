    def _create_host(self, connector):
        """Create a new host on the storage system.

        We create a host name and associate it with the given connection
        information.

        """

        LOG.debug(_('enter: _create_host: host %s') % connector['host'])

        rand_id = str(random.randint(0, 99999999)).zfill(8)
        host_name = '%s-%s' % (self._connector_to_hostname_prefix(connector),
                               rand_id)

        # Get all port information from the connector
        ports = []
        if 'initiator' in connector:
            ports.append('-iscsiname %s' % connector['initiator'])
        if 'wwpns' in connector:
            for wwpn in connector['wwpns']:
                ports.append('-hbawwpn %s' % wwpn)

        # When creating a host, we need one port
        self._driver_assert(len(ports), _('_create_host: No connector ports'))
        port1 = ports.pop(0)
        arg_name, arg_val = port1.split()
        ssh_cmd = ['svctask', 'mkhost', '-force', arg_name, arg_val, '-name',
                   '"%s"' % host_name]
        out, err = self._run_ssh(ssh_cmd)
        self._assert_ssh_return('successfully created' in out,
                                '_create_host', ssh_cmd, out, err)

        # Add any additional ports to the host
        for port in ports:
            arg_name, arg_val = port.split()
            ssh_cmd = ['svctask', 'addhostport', '-force', arg_name, arg_val,
                       host_name]
            out, err = self._run_ssh(ssh_cmd)

        LOG.debug(_('leave: _create_host: host %(host)s - %(host_name)s') %
                  {'host': connector['host'], 'host_name': host_name})
        return host_name
