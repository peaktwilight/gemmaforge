    def _execute_command_and_parse_attributes(self, ssh_cmd):
        """Execute command on the Storwize/SVC and parse attributes.

        Exception is raised if the information from the system
        can not be obtained.

        """

        LOG.debug(_('enter: _execute_command_and_parse_attributes: '
                    ' command %s') % ssh_cmd)

        try:
            out, err = self._run_ssh(ssh_cmd)
        except exception.ProcessExecutionError as e:
            # Didn't get details from the storage, return None
            LOG.error(_('CLI Exception output:\n command: %(cmd)s\n '
                        'stdout: %(out)s\n stderr: %(err)s') %
                      {'cmd': ssh_cmd,
                       'out': e.stdout,
                       'err': e.stderr})
            return None

        self._assert_ssh_return(len(out),
                                '_execute_command_and_parse_attributes',
                                ssh_cmd, out, err)
        attributes = {}
        for attrib_line in out.split('\n'):
            # If '!' not found, return the string and two empty strings
            attrib_name, foo, attrib_value = attrib_line.partition('!')
            if attrib_name is not None and len(attrib_name.strip()):
                attributes[attrib_name] = attrib_value

        LOG.debug(_('leave: _execute_command_and_parse_attributes:\n'
                    'command: %(cmd)s\n'
                    'attributes: %(attr)s')
                  % {'cmd': ssh_cmd,
                     'attr': str(attributes)})

        return attributes
