    def _remove_volume_from_volume_set(self, volume_name, vvs_name):
        self._cli_run('removevvset -f %s %s' % (vvs_name, volume_name), None)
