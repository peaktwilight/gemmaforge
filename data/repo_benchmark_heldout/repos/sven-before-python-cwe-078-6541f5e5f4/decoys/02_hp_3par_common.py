    def _cli_run(self, cmd):
        """Runs a CLI command over SSH, without doing any result parsing."""
        LOG.debug("SSH CMD = %s " % cmd)

        (stdout, stderr) = self._run_ssh(cmd, False)

        # we have to strip out the input and exit lines
        tmp = stdout.split("\r\n")
        out = tmp[5:len(tmp) - 2]
        return out
