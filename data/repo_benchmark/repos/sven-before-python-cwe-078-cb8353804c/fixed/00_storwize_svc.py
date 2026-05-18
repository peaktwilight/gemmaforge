    def do_setup(self, ctxt):
        """Check that we have all configuration details from the storage."""

        LOG.debug(_('enter: do_setup'))
        self._context = ctxt

        # Validate that the pool exists
        ssh_cmd = ['svcinfo', 'lsmdiskgrp', '-delim', '!', '-nohdr']
        out, err = self._run_ssh(ssh_cmd)
        self._assert_ssh_return(len(out.strip()), 'do_setup',
                                ssh_cmd, out, err)
        search_text = '!%s!' % self.configuration.storwize_svc_volpool_name
        if search_text not in out:
            raise exception.InvalidInput(
                reason=(_('pool %s doesn\'t exist')
                        % self.configuration.storwize_svc_volpool_name))

        # Check if compression is supported
        self._compression_enabled = False
        try:
            ssh_cmd = ['svcinfo', 'lslicense', '-delim', '!']
            out, err = self._run_ssh(ssh_cmd)
            license_lines = out.strip().split('\n')
            for license_line in license_lines:
                name, foo, value = license_line.partition('!')
                if name in ('license_compression_enclosures',
                            'license_compression_capacity') and value != '0':
                    self._compression_enabled = True
                    break
        except exception.ProcessExecutionError:
            LOG.exception(_('Failed to get license information.'))

        # Get the iSCSI and FC names of the Storwize/SVC nodes
        ssh_cmd = ['svcinfo', 'lsnode', '-delim', '!']
        out, err = self._run_ssh(ssh_cmd)
        self._assert_ssh_return(len(out.strip()), 'do_setup',
                                ssh_cmd, out, err)

        nodes = out.strip().split('\n')
        self._assert_ssh_return(len(nodes),
                                'do_setup', ssh_cmd, out, err)
        header = nodes.pop(0)
        for node_line in nodes:
            try:
                node_data = self._get_hdr_dic(header, node_line, '!')
            except exception.VolumeBackendAPIException:
                with excutils.save_and_reraise_exception():
                    self._log_cli_output_error('do_setup',
                                               ssh_cmd, out, err)
            node = {}
            try:
                node['id'] = node_data['id']
                node['name'] = node_data['name']
                node['IO_group'] = node_data['IO_group_id']
                node['iscsi_name'] = node_data['iscsi_name']
                node['WWNN'] = node_data['WWNN']
                node['status'] = node_data['status']
                node['WWPN'] = []
                node['ipv4'] = []
                node['ipv6'] = []
                node['enabled_protocols'] = []
                if node['status'] == 'online':
                    self._storage_nodes[node['id']] = node
            except KeyError:
                self._handle_keyerror('lsnode', header)

        # Get the iSCSI IP addresses and WWPNs of the Storwize/SVC nodes
        self._get_iscsi_ip_addrs()
        self._get_fc_wwpns()

        # For each node, check what connection modes it supports.  Delete any
        # nodes that do not support any types (may be partially configured).
        to_delete = []
        for k, node in self._storage_nodes.iteritems():
            if ((len(node['ipv4']) or len(node['ipv6']))
                    and len(node['iscsi_name'])):
                node['enabled_protocols'].append('iSCSI')
                self._enabled_protocols.add('iSCSI')
            if len(node['WWPN']):
                node['enabled_protocols'].append('FC')
                self._enabled_protocols.add('FC')
            if not len(node['enabled_protocols']):
                to_delete.append(k)

        for delkey in to_delete:
            del self._storage_nodes[delkey]

        # Make sure we have at least one node configured
        self._driver_assert(len(self._storage_nodes),
                            _('do_setup: No configured nodes'))

        LOG.debug(_('leave: do_setup'))
