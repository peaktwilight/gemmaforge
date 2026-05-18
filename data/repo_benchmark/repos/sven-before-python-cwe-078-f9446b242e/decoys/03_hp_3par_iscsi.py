    def _get_least_used_nsp(self, nspss):
        """"Return the nsp that has the fewest active vluns."""
        # return only the nsp (node:server:port)
        result = self.common._cli_run(['showvlun', '-a', '-showcols', 'Port'])

        # count the number of nsps (there is 1 for each active vlun)
        nsp_counts = {}
        for nsp in nspss:
            # initialize counts to zero
            nsp_counts[nsp] = 0

        current_least_used_nsp = None
        if result:
            # first line is header
            result = result[1:]
            for line in result:
                nsp = line.strip()
                if nsp in nsp_counts:
                    nsp_counts[nsp] = nsp_counts[nsp] + 1

            # identify key (nsp) of least used nsp
            current_smallest_count = sys.maxint
            for (nsp, count) in nsp_counts.iteritems():
                if count < current_smallest_count:
                    current_least_used_nsp = nsp
                    current_smallest_count = count

        return current_least_used_nsp
