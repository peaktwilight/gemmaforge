    def _add_volume_to_volume_set(self, volume, volume_name,
                                  cpg, vvs_name, qos):
        if vvs_name is not None:
            # Admin has set a volume set name to add the volume to
            self._cli_run('createvvset -add %s %s' % (vvs_name,
                                                      volume_name), None)
        else:
            vvs_name = self._get_3par_vvs_name(volume['id'])
            domain = self.get_domain(cpg)
            self._cli_run('createvvset -domain %s %s' % (domain,
                                                         vvs_name), None)
            self._set_qos_rule(qos, vvs_name)
            self._cli_run('createvvset -add %s %s' % (vvs_name,
                                                      volume_name), None)
