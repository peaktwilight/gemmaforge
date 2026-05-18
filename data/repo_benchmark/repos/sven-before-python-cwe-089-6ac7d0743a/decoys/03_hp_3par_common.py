    def _get_3par_hostname_from_wwn_iqn(self, wwns_iqn):
        out = self._cli_run(['showhost', '-d'])
        # wwns_iqn may be a list of strings or a single
        # string. So, if necessary, create a list to loop.
        if not isinstance(wwns_iqn, list):
            wwn_iqn_list = [wwns_iqn]
        else:
            wwn_iqn_list = wwns_iqn

        for wwn_iqn in wwn_iqn_list:
            for showhost in out:
                if (wwn_iqn.upper() in showhost.upper()):
                    return showhost.split(',')[1]
