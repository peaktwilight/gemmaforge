    def _make_fc_map(self, source, target, full_copy):
        copyflag = '' if full_copy else '-copyrate 0'
        fc_map_cli_cmd = ('svctask mkfcmap -source %(src)s -target %(tgt)s '
                          '-autodelete %(copyflag)s' %
                          {'src': source,
                           'tgt': target,
                           'copyflag': copyflag})
        out, err = self._run_ssh(fc_map_cli_cmd)
        self._driver_assert(
            len(out.strip()),
            _('create FC mapping from %(source)s to %(target)s - '
              'did not find success message in CLI output.\n'
              ' stdout: %(out)s\n stderr: %(err)s\n')
            % {'source': source,
               'target': target,
               'out': str(out),
               'err': str(err)})

        # Ensure that the output is as expected
        match_obj = re.search('FlashCopy Mapping, id \[([0-9]+)\], '
                              'successfully created', out)
        # Make sure we got a "successfully created" message with vdisk id
        self._driver_assert(
            match_obj is not None,
            _('create FC mapping from %(source)s to %(target)s - '
              'did not find success message in CLI output.\n'
              ' stdout: %(out)s\n stderr: %(err)s\n')
            % {'source': source,
               'target': target,
               'out': str(out),
               'err': str(err)})

        try:
            fc_map_id = match_obj.group(1)
            self._driver_assert(
                fc_map_id is not None,
                _('create FC mapping from %(source)s to %(target)s - '
                  'did not find mapping id in CLI output.\n'
                  ' stdout: %(out)s\n stderr: %(err)s\n')
                % {'source': source,
                   'target': target,
                   'out': str(out),
                   'err': str(err)})
        except IndexError:
            self._driver_assert(
                False,
                _('create FC mapping from %(source)s to %(target)s - '
                  'did not find mapping id in CLI output.\n'
                  ' stdout: %(out)s\n stderr: %(err)s\n')
                % {'source': source,
                   'target': target,
                   'out': str(out),
                   'err': str(err)})
        return fc_map_id
