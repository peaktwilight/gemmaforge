    def _create_3par_vlun(self, volume, hostname):
        out = self._cli_run('createvlun %s auto %s' % (volume, hostname), None)
        if out and len(out) > 1:
            if "must be in the same domain" in out[0]:
                err = out[0].strip()
                err = err + " " + out[1].strip()
                raise exception.Invalid3PARDomain(err=err)
