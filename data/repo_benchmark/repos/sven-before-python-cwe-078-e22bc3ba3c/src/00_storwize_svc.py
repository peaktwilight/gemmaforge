    def _get_vdisk_fc_mappings(self, vdisk_name):
        """Return FlashCopy mappings that this vdisk is associated with."""

        ssh_cmd = 'svcinfo lsvdiskfcmappings -nohdr %s' % vdisk_name
        out, err = self._run_ssh(ssh_cmd)

        mapping_ids = []
        if (len(out.strip())):
            lines = out.strip().split('\n')
            mapping_ids = [line.split()[0] for line in lines]
        return mapping_ids
