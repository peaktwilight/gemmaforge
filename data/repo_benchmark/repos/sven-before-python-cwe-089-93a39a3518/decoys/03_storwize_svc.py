    def _ensure_vdisk_no_fc_mappings(self, name, allow_snaps=True):
        # Ensure vdisk has no FlashCopy mappings
        mapping_ids = self._get_vdisk_fc_mappings(name)
        while len(mapping_ids):
            wait_for_copy = False
            for map_id in mapping_ids:
                attrs = self._get_flashcopy_mapping_attributes(map_id)
                if not attrs:
                    continue
                source = attrs['source_vdisk_name']
                target = attrs['target_vdisk_name']
                copy_rate = attrs['copy_rate']
                status = attrs['status']

                if copy_rate == '0':
                    # Case #2: A vdisk that has snapshots
                    if source == name:
                        if not allow_snaps:
                            return False
                        ssh_cmd = ['svctask', 'chfcmap', '-copyrate', '50',
                                   '-autodelete', 'on', map_id]
                        out, err = self._run_ssh(ssh_cmd)
                        wait_for_copy = True
                    # Case #3: A snapshot
                    else:
                        msg = (_('Vdisk %(name)s not involved in '
                                 'mapping %(src)s -> %(tgt)s') %
                               {'name': name, 'src': source, 'tgt': target})
                        self._driver_assert(target == name, msg)
                        if status in ['copying', 'prepared']:
                            self._run_ssh(['svctask', 'stopfcmap', map_id])
                        elif status in ['stopping', 'preparing']:
                            wait_for_copy = True
                        else:
                            self._run_ssh(['svctask', 'rmfcmap', '-force',
                                           map_id])
                # Case 4: Copy in progress - wait and will autodelete
                else:
                    if status == 'prepared':
                        self._run_ssh(['svctask', 'stopfcmap', map_id])
                        self._run_ssh(['svctask', 'rmfcmap', '-force', map_id])
                    elif status == 'idle_or_copied':
                        # Prepare failed
                        self._run_ssh(['svctask', 'rmfcmap', '-force', map_id])
                    else:
                        wait_for_copy = True
            if wait_for_copy:
                time.sleep(5)
            mapping_ids = self._get_vdisk_fc_mappings(name)
        return True
