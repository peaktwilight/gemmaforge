    def _cli_run(self, verb, cli_args):
        """Runs a CLI command over SSH, without doing any result parsing."""
        cli_arg_strings = []
        if cli_args:
            for k, v in cli_args.items():
                if k == '':
                    cli_arg_strings.append(" %s" % k)
                else:
                    cli_arg_strings.append(" %s=%s" % (k, v))

        cmd = verb + ''.join(cli_arg_strings)
        LOG.debug("SSH CMD = %s " % cmd)

        (stdout, stderr) = self._run_ssh(cmd, False)

        # we have to strip out the input and exit lines
        tmp = stdout.split("\r\n")
        out = tmp[5:len(tmp) - 2]
        return out
