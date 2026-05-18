    def _port_conf_generator(self, cmd):
        ssh_cmd = cmd + ['-delim', '!']
        out, err = self._run_ssh(ssh_cmd)

        if not len(out.strip()):
            return
        port_lines = out.strip().split('\n')
        if not len(port_lines):
            return

        header = port_lines.pop(0)
        yield header
        for portip_line in port_lines:
            try:
                port_data = self._get_hdr_dic(header, portip_line, '!')
            except exception.VolumeBackendAPIException:
                with excutils.save_and_reraise_exception():
                    self._log_cli_output_error('_port_conf_generator',
                                               ssh_cmd, out, err)
            yield port_data
