    def extend_volume(self, volume, new_size):
        LOG.debug(_('enter: extend_volume: volume %s') % volume['id'])
        ret = self._ensure_vdisk_no_fc_mappings(volume['name'],
                                                allow_snaps=False)
        if not ret:
            exception_message = (_('extend_volume: Extending a volume with '
                                   'snapshots is not supported.'))
            raise exception.VolumeBackendAPIException(data=exception_message)

        extend_amt = int(new_size) - volume['size']
        ssh_cmd = ('svctask expandvdisksize -size %(amt)d -unit gb %(name)s'
                   % {'amt': extend_amt, 'name': volume['name']})
        out, err = self._run_ssh(ssh_cmd)
        # No output should be returned from expandvdisksize
        self._assert_ssh_return(len(out.strip()) == 0, 'extend_volume',
                                ssh_cmd, out, err)
        LOG.debug(_('leave: extend_volume: volume %s') % volume['id'])
