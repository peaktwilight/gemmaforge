    def _delete_vdisk(self, name, force):
        """Deletes existing vdisks.

        It is very important to properly take care of mappings before deleting
        the disk:
        1. If no mappings, then it was a vdisk, and can be deleted
        2. If it is the source of a flashcopy mapping and copy_rate is 0, then
           it is a vdisk that has a snapshot.  If the force flag is set,
           delete the mapping and the vdisk, otherwise set the mapping to
           copy and wait (this will allow users to delete vdisks that have
           snapshots if/when the upper layers allow it).
        3. If it is the target of a mapping and copy_rate is 0, it is a
           snapshot, and we should properly stop the mapping and delete.
        4. If it is the source/target of a mapping and copy_rate is not 0, it
           is a clone or vdisk created from a snapshot.  We wait for the copy
           to complete (the mapping will be autodeleted) and then delete the
           vdisk.

        """

        LOG.debug(_('enter: _delete_vdisk: vdisk %s') % name)

        # Try to delete volume only if found on the storage
        vdisk_defined = self._is_vdisk_defined(name)
        if not vdisk_defined:
            LOG.info(_('warning: Tried to delete vdisk %s but it does not '
                       'exist.') % name)
            return

        self._ensure_vdisk_no_fc_mappings(name)

        ssh_cmd = ['svctask', 'rmvdisk', '-force', name]
        if not force:
            ssh_cmd.remove('-force')
        out, err = self._run_ssh(ssh_cmd)
        # No output should be returned from rmvdisk
        self._assert_ssh_return(len(out.strip()) == 0,
                                ('_delete_vdisk %(name)s')
                                % {'name': name},
                                ssh_cmd, out, err)
        LOG.debug(_('leave: _delete_vdisk: vdisk %s') % name)
