    def _create_vdisk(self, name, size, units, opts):
        """Create a new vdisk."""

        LOG.debug(_('enter: _create_vdisk: vdisk %s ') % name)

        model_update = None
        autoex = '-autoexpand' if opts['autoexpand'] else ''
        easytier = '-easytier on' if opts['easytier'] else '-easytier off'

        # Set space-efficient options
        if opts['rsize'] == -1:
            ssh_cmd_se_opt = ''
        else:
            ssh_cmd_se_opt = (
                '-rsize %(rsize)d%% %(autoex)s -warning %(warn)d%%' %
                {'rsize': opts['rsize'],
                 'autoex': autoex,
                 'warn': opts['warning']})
            if opts['compression']:
                ssh_cmd_se_opt = ssh_cmd_se_opt + ' -compressed'
            else:
                ssh_cmd_se_opt = ssh_cmd_se_opt + (
                    ' -grainsize %d' % opts['grainsize'])

        ssh_cmd = ('svctask mkvdisk -name %(name)s -mdiskgrp %(mdiskgrp)s '
                   '-iogrp 0 -size %(size)s -unit '
                   '%(unit)s %(easytier)s %(ssh_cmd_se_opt)s'
                   % {'name': name,
                   'mdiskgrp': self.configuration.storwize_svc_volpool_name,
                   'size': size, 'unit': units, 'easytier': easytier,
                   'ssh_cmd_se_opt': ssh_cmd_se_opt})
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
