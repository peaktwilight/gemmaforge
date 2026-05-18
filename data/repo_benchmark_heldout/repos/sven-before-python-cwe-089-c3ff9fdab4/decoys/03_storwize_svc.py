    def _map_vol_to_host(self, volume_name, host_name):
        """Create a mapping between a volume to a host."""

        LOG.debug(_('enter: _map_vol_to_host: volume %(volume_name)s to '
                    'host %(host_name)s')
                  % {'volume_name': volume_name, 'host_name': host_name})

        # Check if this volume is already mapped to this host
        mapping_data = self._get_hostvdisk_mappings(host_name)

        mapped_flag = False
        result_lun = '-1'
        if volume_name in mapping_data:
            mapped_flag = True
            result_lun = mapping_data[volume_name]['SCSI_id']
        else:
            lun_used = [int(v['SCSI_id']) for v in mapping_data.values()]
            lun_used.sort()
            # Assume all luns are taken to this point, and then try to find
            # an unused one
            result_lun = str(len(lun_used))
            for index, n in enumerate(lun_used):
                if n > index:
                    result_lun = str(index)
                    break

        # Volume is not mapped to host, create a new LUN
        if not mapped_flag:
            ssh_cmd = ['svctask', 'mkvdiskhostmap', '-host', host_name,
                       '-scsi', result_lun, volume_name]
            out, err = self._run_ssh(ssh_cmd, check_exit_code=False)
            if err and err.startswith('CMMVC6071E'):
                if not self.configuration.storwize_svc_multihostmap_enabled:
                    LOG.error(_('storwize_svc_multihostmap_enabled is set '
                                'to False, Not allow multi host mapping'))
                    exception_msg = 'CMMVC6071E The VDisk-to-host mapping '\
                                    'was not created because the VDisk is '\
                                    'already mapped to a host.\n"'
                    raise exception.CinderException(data=exception_msg)

                for i in range(len(ssh_cmd)):
                    if ssh_cmd[i] == 'mkvdiskhostmap':
                        ssh_cmd.insert(i + 1, '-force')

                # try to map one volume to multiple hosts
                out, err = self._run_ssh(ssh_cmd)
                LOG.warn(_('volume %s mapping to multi host') % volume_name)
                self._assert_ssh_return('successfully created' in out,
                                        '_map_vol_to_host', ssh_cmd, out, err)
            else:
                self._assert_ssh_return('successfully created' in out,
                                        '_map_vol_to_host', ssh_cmd, out, err)
        LOG.debug(_('leave: _map_vol_to_host: LUN %(result_lun)s, volume '
                    '%(volume_name)s, host %(host_name)s') %
                  {'result_lun': result_lun,
                   'volume_name': volume_name,
                   'host_name': host_name})
        return result_lun
