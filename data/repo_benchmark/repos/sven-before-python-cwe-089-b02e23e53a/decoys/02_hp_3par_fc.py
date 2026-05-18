    def _create_3par_fibrechan_host(self, hostname, wwns, domain, persona_id):
        """Create a 3PAR host.

        Create a 3PAR host, if there is already a host on the 3par using
        the same wwn but with a different hostname, return the hostname
        used by 3PAR.
        """
        command = ['createhost', '-persona', persona_id, '-domain', domain,
                   hostname]
        for wwn in wwns:
            command.append(wwn)

        out = self.common._cli_run(command)
        if out and len(out) > 1:
            return self.common.parse_create_host_error(hostname, out)

        return hostname
