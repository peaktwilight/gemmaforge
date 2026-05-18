    def extend_volume(self, volume, new_size):
        volume_name = self._get_3par_vol_name(volume['id'])
        old_size = volume.size
        growth_size = int(new_size) - old_size
        LOG.debug("Extending Volume %s from %s to %s, by %s GB." %
                  (volume_name, old_size, new_size, growth_size))
        try:
            self._cli_run(['growvv', '-f', volume_name, '%dg' % growth_size])
        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.error(_("Error extending volume %s") % volume)
