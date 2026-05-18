    def _create_3par_fibrechan_host(self, hostname, wwn, domain, persona_id):
        """Create a 3PAR host.

        Create a 3PAR host, if there is already a host on the 3par using
        the same wwn but with a different hostname, return the hostname
        used by 3PAR.
        """
        out = self.common._cli_run('createhost -persona %s -domain %s %s %s'
                                   % (persona_id, domain,
                                      hostname, " ".join(wwn)), None)
        if out and len(out) > 1:
            return self.common.parse_create_host_error(hostname, out)

        return hostname
