    def _call_prepare_fc_map(self, fc_map_id, source, target):
        try:
            out, err = self._run_ssh('svctask prestartfcmap %s' % fc_map_id)
        except exception.ProcessExecutionError as e:
            with excutils.save_and_reraise_exception():
                LOG.error(_('_prepare_fc_map: Failed to prepare FlashCopy '
                            'from %(source)s to %(target)s.\n'
                            'stdout: %(out)s\n stderr: %(err)s')
                          % {'source': source,
                             'target': target,
                             'out': e.stdout,
                             'err': e.stderr})
