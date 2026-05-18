    def _cliq_run(self, verb, cliq_args, check_exit_code=True):
        """Runs a CLIQ command over SSH, without doing any result parsing"""
        cmd_list = [verb]
        for k, v in cliq_args.items():
            cmd_list.append("%s=%s" % (k, v))

        return self._run_ssh(cmd_list, check_exit_code)
