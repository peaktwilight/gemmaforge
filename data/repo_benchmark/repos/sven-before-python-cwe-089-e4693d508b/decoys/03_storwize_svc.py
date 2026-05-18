    def _create_vdisk(self, name, size, units, opts):
        """Create a new vdisk."""

        LOG.debug(_('enter: _create_vdisk: vdisk %s ') % name)

        model_update = None
        easytier = 'on' if opts['easytier'] else 'off'

        # Set space-efficient options
        if opts['rsize'] == -1:
            ssh_cmd_se_opt = []
        else:
            ssh_cmd_se_opt = ['-rsize', '%s%%' % str(opts['rsize']),
                              '-autoexpand', '-warning',
                              '%s%%' % str(opts['warning'])]
            if not opts['autoexpand']:
                ssh_cmd_se_opt.remove('-autoexpand')

            if opts['compression']:
                ssh_cmd_se_opt.append('-compressed')
            else:
                ssh_cmd_se_opt.extend(['-grainsize', str(opts['grainsize'])])

        ssh_cmd = ['svctask', 'mkvdisk', '-name', name, '-mdiskgrp',
                   self.configuration.storwize_svc_volpool_name,
                   '-iogrp', '0', '-size', size, '-unit',
                   units, '-easytier', easytier] + ssh_cmd_se_opt
        out, err = self._run_ssh(ssh_cmd)
        self._assert_ssh_return(len(out.strip()), '_create_vdisk',
                                ssh_cmd, out, err)

        # Ensure that the output is as expected
        match_obj = re.search('Virtual Disk, id \[([0-9]+)\], '
                              'successfully created', out)
        # Make sure we got a "successfully created" message with vdisk id
        self._driver_assert(
            match_obj is not None,
            _('_create_vdisk %(name)s - did not find '
              'success message in CLI output.\n '
              'stdout: %(out)s\n stderr: %(err)s')
            % {'name': name, 'out': str(out), 'err': str(err)})

        LOG.debug(_('leave: _create_vdisk: volume %s ') % name)
