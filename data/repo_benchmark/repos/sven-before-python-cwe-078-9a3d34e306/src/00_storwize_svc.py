    def terminate_connection(self, volume, connector, **kwargs):
        """Cleanup after an iSCSI connection has been terminated.

        When we clean up a terminated connection between a given connector
        and volume, we:
        1. Translate the given connector to a host name
        2. Remove the volume-to-host mapping if it exists
        3. Delete the host if it has no more mappings (hosts are created
           automatically by this driver when mappings are created)
        """
        LOG.debug(_('enter: terminate_connection: volume %(vol)s with '
                    'connector %(conn)s') % {'vol': str(volume),
                                             'conn': str(connector)})

        vol_name = volume['name']
        host_name = self._get_host_from_connector(connector)
        # Verify that _get_host_from_connector returned the host.
        # This should always succeed as we terminate an existing connection.
        self._driver_assert(
            host_name is not None,
            _('_get_host_from_connector failed to return the host name '
              'for connector'))

        # Check if vdisk-host mapping exists, remove if it does
        mapping_data = self._get_hostvdisk_mappings(host_name)
        if vol_name in mapping_data:
            ssh_cmd = 'svctask rmvdiskhostmap -host %s %s' % \
                (host_name, vol_name)
            out, err = self._run_ssh(ssh_cmd)
            # Verify CLI behaviour - no output is returned from
            # rmvdiskhostmap
            self._assert_ssh_return(len(out.strip()) == 0,
                                    'terminate_connection', ssh_cmd, out, err)
            del mapping_data[vol_name]
        else:
            LOG.error(_('terminate_connection: No mapping of volume '
                        '%(vol_name)s to host %(host_name)s found') %
                      {'vol_name': vol_name, 'host_name': host_name})

        # If this host has no more mappings, delete it
        if not mapping_data:
            self._delete_host(host_name)

        LOG.debug(_('leave: terminate_connection: volume %(vol)s with '
                    'connector %(conn)s') % {'vol': str(volume),
                                             'conn': str(connector)})
