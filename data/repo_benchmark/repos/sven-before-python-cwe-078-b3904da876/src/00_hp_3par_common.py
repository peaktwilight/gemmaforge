    def _set_qos_rule(self, qos, vvs_name):
        max_io = self._get_qos_value(qos, 'maxIOPS')
        max_bw = self._get_qos_value(qos, 'maxBWS')
        cli_qos_string = ""
        if max_io is not None:
            cli_qos_string += ('-io %s ' % max_io)
        if max_bw is not None:
            cli_qos_string += ('-bw %sM ' % max_bw)
        self._cli_run('setqos %svvset:%s' %
                      (cli_qos_string, vvs_name), None)
