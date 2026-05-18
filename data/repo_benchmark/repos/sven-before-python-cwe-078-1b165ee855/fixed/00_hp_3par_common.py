    def _get_vvset_from_3par(self, volume_name):
        """Get Virtual Volume Set from 3PAR.

        The only way to do this currently is to try and delete the volume
        to get the error message.

        NOTE(walter-boring): don't call this unless you know the volume is
        already in a vvset!
        """
        cmd = ['removevv', '-f', volume_name]
        LOG.debug("Issuing remove command to find vvset name %s" % cmd)
        out = self._cli_run(cmd)
        vvset_name = None
        if out and len(out) > 1:
            if out[1].startswith("Attempt to delete "):
                words = out[1].split(" ")
                vvset_name = words[len(words) - 1]

        return vvset_name
