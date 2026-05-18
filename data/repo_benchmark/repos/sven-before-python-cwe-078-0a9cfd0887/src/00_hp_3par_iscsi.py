    def _create_3par_iscsi_host(self, hostname, iscsi_iqn, domain, persona_id):
        """Create a 3PAR host.

        Create a 3PAR host, if there is already a host on the 3par using
        the same iqn but with a different hostname, return the hostname
        used by 3PAR.
        """
        cmd = 'createhost -iscsi -persona %s -domain %s %s %s' % \
              (persona_id, domain, hostname, iscsi_iqn)
        out = self.common._cli_run(cmd, None)
        if out and len(out) > 1:
            return self.common.parse_create_host_error(hostname, out)
        return hostname
