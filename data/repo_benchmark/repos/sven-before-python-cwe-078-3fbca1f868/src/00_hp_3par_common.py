    def _remove_volume_set(self, vvs_name):
        # Must first clear the QoS rules before removing the volume set
        self._cli_run('setqos -clear vvset:%s' % (vvs_name), None)
        self._cli_run('removevvset -f %s' % (vvs_name), None)
