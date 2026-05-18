    def _add_chapsecret_to_host(self, host_name):
        """Generate and store a randomly-generated CHAP secret for the host."""

        chap_secret = utils.generate_password()
        ssh_cmd = ('svctask chhost -chapsecret "%(chap_secret)s" %(host_name)s'
                   % {'chap_secret': chap_secret, 'host_name': host_name})
        out, err = self._run_ssh(ssh_cmd)
        # No output should be returned from chhost
        self._assert_ssh_return(len(out.strip()) == 0,
                                '_add_chapsecret_to_host', ssh_cmd, out, err)
        return chap_secret
