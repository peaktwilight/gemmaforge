    def _find_host_exhaustive(self, connector, hosts):
        for host in hosts:
            ssh_cmd = 'svcinfo lshost -delim ! %s' % host
            out, err = self._run_ssh(ssh_cmd)
            self._assert_ssh_return(len(out.strip()),
                                    '_find_host_exhaustive',
                                    ssh_cmd, out, err)
            for attr_line in out.split('\n'):
                # If '!' not found, return the string and two empty strings
                attr_name, foo, attr_val = attr_line.partition('!')
                if (attr_name == 'iscsi_name' and
                        'initiator' in connector and
                        attr_val == connector['initiator']):
                    return host
                elif (attr_name == 'WWPN' and
                      'wwpns' in connector and
                      attr_val.lower() in
                      map(str.lower, map(str, connector['wwpns']))):
                        return host
        return None
