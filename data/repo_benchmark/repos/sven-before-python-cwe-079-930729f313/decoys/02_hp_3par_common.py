    def _set_connections(self):
        """Set the number of concurrent connections.

        The 3PAR WS API server has a limit of concurrent connections.
        This is setting the number to the highest allowed, 15 connections.
        """
        self._cli_run(['setwsapi', '-sru', 'high'])
