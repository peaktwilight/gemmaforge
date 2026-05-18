    def initialize_connection(self, volume, connector):
        """Restrict access to a volume."""
        try:
            cmd = ['volume', 'select', volume['name'], 'access', 'create',
                   'initiator', connector['initiator']]
            if self.configuration.eqlx_use_chap:
                cmd.extend(['authmethod chap', 'username',
                            self.configuration.eqlx_chap_login])
            self._eql_execute(*cmd)
            iscsi_properties = self._get_iscsi_properties(volume)
            return {
                'driver_volume_type': 'iscsi',
                'data': iscsi_properties
            }
        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.error(_('Failed to initialize connection to volume %s'),
                          volume['name'])
