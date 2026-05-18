    def _add_volume_to_volume_set(self, volume, volume_name,
                                  cpg, vvs_name, qos):
        if vvs_name is not None:
            # Admin has set a volume set name to add the volume to
            self._cli_run(['createvvset', '-add', vvs_name, volume_name])
        else:
            vvs_name = self._get_3par_vvs_name(volume['id'])
            domain = self.get_domain(cpg)
            self._cli_run(['createvvset', '-domain', domain, vvs_name])
            self._set_qos_rule(qos, vvs_name)
            self._cli_run(['createvvset', '-add', vvs_name, volume_name])
