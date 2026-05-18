    def _get_fc_wwpns(self):
        for key in self._storage_nodes:
            node = self._storage_nodes[key]
            ssh_cmd = ['svcinfo', 'lsnode', '-delim', '!', node['id']]
            raw = self._run_ssh(ssh_cmd)
            resp = CLIResponse(raw, delim='!', with_header=False)
            wwpns = set(node['WWPN'])
            for i, s in resp.select('port_id', 'port_status'):
                if 'unconfigured' != s:
                    wwpns.add(i)
            node['WWPN'] = list(wwpns)
            LOG.info(_('WWPN on node %(node)s: %(wwpn)s')
                     % {'node': node['id'], 'wwpn': node['WWPN']})
