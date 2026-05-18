    def _get_iscsi_ip_addrs(self):
        generator = self._port_conf_generator(['svcinfo', 'lsportip'])
        header = next(generator, None)
        if not header:
            return

        for port_data in generator:
            try:
                port_node_id = port_data['node_id']
                port_ipv4 = port_data['IP_address']
                port_ipv6 = port_data['IP_address_6']
                state = port_data['state']
            except KeyError:
                self._handle_keyerror('lsportip', header)

            if port_node_id in self._storage_nodes and (
                    state == 'configured' or state == 'online'):
                node = self._storage_nodes[port_node_id]
                if len(port_ipv4):
                    node['ipv4'].append(port_ipv4)
                if len(port_ipv6):
                    node['ipv6'].append(port_ipv6)
