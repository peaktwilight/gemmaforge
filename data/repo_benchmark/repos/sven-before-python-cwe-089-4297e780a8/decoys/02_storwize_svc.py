    def _start_fc_map(self, fc_map_id, source, target):
        try:
            out, err = self._run_ssh(['svctask', 'startfcmap', fc_map_id])
        except exception.ProcessExecutionError as e:
            with excutils.save_and_reraise_exception():
                LOG.error(_('_start_fc_map: Failed to start FlashCopy '
                            'from %(source)s to %(target)s.\n'
                            'stdout: %(out)s\n stderr: %(err)s')
                          % {'source': source,
                             'target': target,
                             'out': e.stdout,
                             'err': e.stderr})
