    def _get_active_nsp(self, hostname):
        """Return the active nsp, if one exists, for the given host."""
        result = self.common._cli_run(['showvlun', '-a', '-host', hostname])
        if result:
            # first line is header
            result = result[1:]
            for line in result:
                info = line.split(",")
                if info and len(info) > 4:
                    return info[4]
