    def _find_host_from_wwpn(self, connector):
        for wwpn in connector['wwpns']:
            ssh_cmd = 'svcinfo lsfabric -wwpn %s -delim !' % wwpn
            out, err = self._run_ssh(ssh_cmd)

            if not len(out.strip()):
                # This WWPN is not in use
                continue

            host_lines = out.strip().split('\n')
            header = host_lines.pop(0).split('!')
            self._assert_ssh_return('remote_wwpn' in header and
                                    'name' in header,
                                    '_find_host_from_wwpn',
                                    ssh_cmd, out, err)
            rmt_wwpn_idx = header.index('remote_wwpn')
            name_idx = header.index('name')

            wwpns = map(lambda x: x.split('!')[rmt_wwpn_idx], host_lines)

            if wwpn in wwpns:
                # All the wwpns will be the mapping for the same
                # host from this WWPN-based query. Just pick
                # the name from first line.
                hostname = host_lines[0].split('!')[name_idx]
                return hostname

        # Didn't find a host
        return None
