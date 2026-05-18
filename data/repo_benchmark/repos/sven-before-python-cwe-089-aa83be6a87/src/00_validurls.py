    def analyze_smashgg(self, urls, name):
        LOG.info('we are about to analyze scene {} with {} brackets'.format(name, len(urls)))
        for url in urls:
            # Before we process this URL, check to see if we already have
            sql = "SELECT * FROM analyzed where base_url='{}'".format(url)
            res = self.db.exec(sql)
            if len(res) == 0:

                display_name = bracket_utils.get_display_base(url)

                # We don't care about doubles tournaments
                if 'doubles' in display_name.lower() or 'dubs' in display_name.lower():
                    LOG.info('We are skipping the tournament {} because it is a doubles tournament'.format(display_name))
                    continue

                LOG.info('About to process pro bracket {}'.format(url))
                self.data_processor.process(url, name, display_name)
            else:
                LOG.info("Skpping pro bracket because it has already been analyzed: {}".format(url))
