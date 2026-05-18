    def _get_conn_fc_wwpns(self, host_name):
        wwpns = []
        cmd = ['svcinfo', 'lsfabric', '-host', host_name]
        generator = self._port_conf_generator(cmd)
        header = next(generator, None)
        if not header:
            return wwpns

        for port_data in generator:
            try:
                wwpns.append(port_data['local_wwpn'])
            except KeyError as e:
                self._handle_keyerror('lsfabric', header)

        return wwpns
