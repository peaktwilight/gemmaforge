    def _copy_volume(self, src_name, dest_name, cpg=None, snap_cpg=None,
                     tpvv=True):
        # Virtual volume sets are not supported with the -online option
        cmd = ['createvvcopy', '-p', src_name, '-online']
        if snap_cpg:
            cmd.extend(['-snp_cpg', snap_cpg])
        if tpvv:
            cmd.append('-tpvv')
        if cpg:
            cmd.append(cpg)
        cmd.append(dest_name)
        LOG.debug('Creating clone of a volume with %s' % cmd)
        self._cli_run(cmd)
