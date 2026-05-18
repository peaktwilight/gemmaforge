    def _update_volume_stats(self):
        """Retrieve stats info from volume group."""

        LOG.debug(_("Updating volume stats"))
        data = {}

        data['vendor_name'] = 'IBM'
        data['driver_version'] = '1.1'
        data['storage_protocol'] = list(self._enabled_protocols)

        data['total_capacity_gb'] = 0  # To be overwritten
        data['free_capacity_gb'] = 0   # To be overwritten
        data['reserved_percentage'] = 0
        data['QoS_support'] = False

        pool = self.configuration.storwize_svc_volpool_name
        #Get storage system name
        ssh_cmd = ['svcinfo', 'lssystem', '-delim', '!']
        attributes = self._execute_command_and_parse_attributes(ssh_cmd)
        if not attributes or not attributes['name']:
            exception_message = (_('_update_volume_stats: '
                                   'Could not get system name'))
            raise exception.VolumeBackendAPIException(data=exception_message)

        backend_name = self.configuration.safe_get('volume_backend_name')
        if not backend_name:
            backend_name = '%s_%s' % (attributes['name'], pool)
        data['volume_backend_name'] = backend_name

        ssh_cmd = ['svcinfo', 'lsmdiskgrp', '-bytes', '-delim', '!', pool]
        attributes = self._execute_command_and_parse_attributes(ssh_cmd)
        if not attributes:
            LOG.error(_('Could not get pool data from the storage'))
            exception_message = (_('_update_volume_stats: '
                                   'Could not get storage pool data'))
            raise exception.VolumeBackendAPIException(data=exception_message)

        data['total_capacity_gb'] = (float(attributes['capacity']) /
                                    (1024 ** 3))
        data['free_capacity_gb'] = (float(attributes['free_capacity']) /
                                    (1024 ** 3))
        data['easytier_support'] = attributes['easy_tier'] in ['on', 'auto']
        data['compression_support'] = self._compression_enabled

        self._stats = data
