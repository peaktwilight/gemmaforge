    def _get_flashcopy_mapping_attributes(self, fc_map_id):
        LOG.debug(_('enter: _get_flashcopy_mapping_attributes: mapping %s')
                  % fc_map_id)

        fc_ls_map_cmd = 'svcinfo lsfcmap -filtervalue id=%s -delim !' % \
            fc_map_id
        out, err = self._run_ssh(fc_ls_map_cmd)
        if not len(out.strip()):
            return None

        # Get list of FlashCopy mappings
        # We expect zero or one line if mapping does not exist,
        # two lines if it does exist, otherwise error
        lines = out.strip().split('\n')
        self._assert_ssh_return(len(lines) <= 2,
                                '_get_flashcopy_mapping_attributes',
                                fc_ls_map_cmd, out, err)

        if len(lines) == 2:
            attributes = self._get_hdr_dic(lines[0], lines[1], '!')
        else:  # 0 or 1 lines
            attributes = None

        LOG.debug(_('leave: _get_flashcopy_mapping_attributes: mapping '
                    '%(fc_map_id)s, attributes %(attributes)s') %
                  {'fc_map_id': fc_map_id, 'attributes': attributes})

        return attributes
