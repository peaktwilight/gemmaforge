    def _get_vdisk_attributes(self, vdisk_name):
        """Return vdisk attributes, or None if vdisk does not exist

        Exception is raised if the information from system can not be
        parsed/matched to a single vdisk.
        """

        ssh_cmd = 'svcinfo lsvdisk -bytes -delim ! %s ' % vdisk_name
        return self._execute_command_and_parse_attributes(ssh_cmd)
