    def _copy_volume(self, src_name, dest_name, cpg=None, snap_cpg=None,
                     tpvv=True):
        # Virtual volume sets are not supported with the -online option
        cmd = 'createvvcopy -p %s -online ' % src_name
        if snap_cpg:
            cmd += '-snp_cpg %s ' % snap_cpg
        if tpvv:
            cmd += '-tpvv '
        if cpg:
            cmd += cpg + ' '
        cmd += dest_name
        LOG.debug('Creating clone of a volume with %s' % cmd)
        self._cli_run(cmd, None)
