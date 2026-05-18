    def check_and_update_ranks(self, scene):
        # There are 2 cases here:
        #   1) Ranks have never been calculated for this scene before
        #       - This means we need to calculate what the ranks were every month of this scenes history
        #       - We should only do this if ranks don't already exist for this scene
        #   2) Ranks have been calculated for this scene before
        #       - We already have bulk ranks. We should check if it has been more than 1 month since we last
        #           calculated ranks. If so, calculate again with the brackets that have come out this month

        LOG.info('About to check if ranks need updating for {}'.format(scene))
        # First, do we have any ranks for this scene already?
        sql = 'select count(*) from ranks where scene="{}";'.format(scene)
        res = self.db.exec(sql)
        count = res[0][0]

        n = 5 if (scene == 'pro' or scene == 'pro_wiiu') else constants.TOURNAMENTS_PER_RANK
        if count == 0:
            LOG.info('Detected that we need to bulk update ranks for {}'.format(scene))
            # Alright, we have nothing. Bulk update ranks
            first_month = bracket_utils.get_first_month(self.db, scene)
            last_month = bracket_utils.get_last_month(self.db, scene)
            
            # Iterate through all tournaments going month by month, and calculate ranks
            months = bracket_utils.iter_months(first_month, last_month, include_first=False, include_last=True)
            for month in months:
                urls, _ = bracket_utils.get_n_tournaments_before_date(self.db, scene, month, n)
                self.process_ranks(scene, urls, month)
        else:

            # Get the date of the last time we calculated ranks
            sql = "select date from ranks where scene='{}' order by date desc limit 1;".format(scene)
            res = self.db.exec(sql)
            last_rankings_date = res[0][0]

            # Check to see if it's been more than 1 month since we last calculated ranks
            more_than_one_month = bracket_utils.has_month_passed(last_rankings_date)
            if more_than_one_month:
                # Get only the last n tournaments, so it doesn't take too long to process
                today = datetime.datetime.today().strftime('%Y-%m-%d')
                msg = 'Detected that we need up update monthly ranks for {}, on {}'.format(scene, today)
                LOG.info(msg)

                # We should only ever calculate ranks on the 1st. If today is not the first, log error
                if not today.split('-')[-1] == '1':
                    LOG.exc('We are calculating ranks today, {}, but it isnt the first'.format(today))

                months = bracket_utils.iter_months(last_rankings_date, today, include_first=False, include_last=True)
                for month in months:
                    # Make sure that we actually have matches during this month
                    # Say we are trying to calculate ranks for 2018-05-01, the player would need to have matches during 2018-04-01, 2018-04-30
                    prev_date = bracket_utils.get_previous_month(month)
                    brackets_during_month = bracket_utils.get_tournaments_during_month(self.db, scene, prev_date)

                    if len(brackets_during_month) > 0:
                        tweet('Calculating {} ranks for {}'.format(month, scene))
                        urls, _ = bracket_utils.get_n_tournaments_before_date(self.db, scene, month, n)
                        self.process_ranks(scene, urls, month)

            else:
                LOG.info('It has not yet been 1 month since we calculated ranks for {}. Skipping'.format(scene))
