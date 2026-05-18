    def analyze_scene(self, scene):
        base_urls = scene.get_base_urls()
        users = scene.get_users()
        name = scene.get_name()
        LOG.info('found the following users for scene {}: {}'.format(name, users))

        # This scene might have one user who always posts the brackets on their challonge account
        for user in users:
            # Have we analyzed this user before?
            sql = "SELECT * FROM user_analyzed WHERE user='{}';".format(user)
            results = self.db.exec(sql)

            # Did we have any matches in the database?
            if len(results) > 0:
                # We have analyzed this user before. Just grab one page of brackets to see if there have been any new tournaments
                # eg, just look at /users/christmasmike?page=1 instead of all the pages that exist
                most_recent_page = bracket_utils.get_brackets_from_user(user, pages=1)
                for bracket in most_recent_page:
                    LOG.info('here are the brackets from the most recent page of user {}: {}'.format(user, most_recent_page))
                    # This user has already been analyzed, there's a good chance this bracket has been analyzed also
                    sql = "SELECT * FROM user_analyzed WHERE url='{}' AND user='{}';".format(bracket, user)
                    results = self.db.exec(sql)

                    if len(results) == 0:
                        # This is a new bracket that must have been published in the last hour or so
                        LOG.info('found this url from a user: {} {}'.format(bracket, user))
                        display_name = bracket_utils.get_display_base(bracket)
                        # We don't care about doubles tournaments
                        if 'doubles' in display_name.lower() or 'dubs' in display_name.lower():
                            LOG.info('We are skipping the tournament {} because it is a doubles tournament'.format(display_name))
                            continue

                        self.data_processor.process(bracket, name, display_name)

                        # mark this bracket as analyzed
                        sql = "INSERT INTO user_analyzed (url, user, scene) VALUES ('{}', '{}', '{}');".format(bracket, user, name)
                        self.db.exec(sql)

                        # Tweet that we found a new bracket
                        msg = "Found new {} bracket: {}".format(name, bracket)
                        tweet(msg)
                    else:
                        LOG.info('url {} is not new for user {}'.format(bracket, user))
            else:
                # This is a new user, analyze all brackets
                user_urls = bracket_utils.get_brackets_from_user(user)
                for url in user_urls:
                    LOG.info('found this url from a user: {} {}'.format(url, user))
                    display_name = bracket_utils.get_display_base(url)
                    # We don't care about doubles tournaments
                    if 'doubles' in display_name.lower() or 'dubs' in display_name.lower():
                        LOG.info('We are skipping the tournament {} because it is a doubles tournament'.format(display_name))
                        continue

                    self.data_processor.process(url, name, display_name)

                    # mark this bracket as analyzed
                    sql = "INSERT INTO user_analyzed (url, user, scene) VALUES ('{}', '{}', '{}');".format(url, user, name)
                    self.db.exec(sql)

                LOG.info('done with user {}'.format(user))


        # This scene might always call their brackets the same thing, eg weekly1, weekly2, weekly3 etc
        for base_url in base_urls:
            # attempt to load this data from the database
            LOG.info('About to start this analysis thread for scene {}'.format(scene.get_name()))
            sql = "SELECT first,last FROM valids WHERE base_url = '" + str(base_url) + "';"
            result = self.db.exec(sql)
            has_results = len(result) > 0 

            # Did we find a match in the database?
            if has_results:
                LOG.info("validURLs found values in the database" + str(result))
                first = result[0][0]
                last = result[0][1]

                # Check for a new valid URL
                new_last = bracket_utils._get_last_valid_url(base_url, last-1)

                if not new_last == last:
                    if new_last - last > 5:
                        with open("DEBUGOUTPUT.txt", 'a') as f:
                            f.write("[validURLs.py:55]: found a SHIT TON of new tournaments for bracket: {}".format(base_url))

                    else:
                        bracket = base_url.replace('###', str(new_last))
                        LOG.info('Found new bracket: {}'.format(bracket))
                        msg = "Found new bracket: {}".format(bracket)
                        tweet(msg)

                    # If there's been a new last, update the database
                    sql = "UPDATE valids SET last=" + str(new_last) + " where base_url = '"+str(base_url)+"';"
                    self.db.exec(sql)


                    # Analyze each of these new brackets
                    for i in range(last+1, new_last+1):
                        # Since this URL is new, we have to process the data
                        bracket = base_url.replace('###', str(i))
                        # Create the display name for this bracket
                        # Eg challonge.com/NP9ATX54 -> NP9 54
                        display_name = bracket_utils.get_display_base(bracket, counter=i)
                        # We don't care about doubles tournaments
                        if 'doubles' in display_name.lower() or 'dubs' in display_name.lower():
                            LOG.info('We are skipping the tournament {} because it is a doubles tournament'.format(display_name))
                            continue

                        self.data_processor.process(bracket, name, display_name, new_bracket=True)

            else:
                # We need to create first and last from scratch
                first = bracket_utils._get_first_valid_url(base_url)
                last = bracket_utils._get_last_valid_url(base_url, first)

                # This is new data, we need to put it into the db
                sql = "INSERT INTO valids (base_url, first, last, scene) VALUES ("
                sql += "'"+str(base_url)+"', "+str(first)+ ", "+str(last)+", '"+str(name)+"');"
                self.db.exec(sql)

                for i in range(first, last+1):
                    bracket = base_url.replace('###', str(i))
                    # Create the display name for this bracket
                    # Eg challonge.com/NP9ATX54 -> NP9 54
                    display_name = bracket_utils.get_display_base(bracket, counter=i)
                    # We don't care about doubles tournaments
                    if 'doubles' in display_name.lower() or 'dubs' in display_name.lower():
                        LOG.info('We are skipping the tournament {} because it is a doubles tournament'.format(display_name))
                        continue

                    self.data_processor.process(bracket, name, display_name)

                    # Calculate ranks after each tournament so we can see how players are progressing
        if not analyzed_scenes and should_tweet:
            tweet('About to start ranking for scene {}'.format(name))
        self.data_processor.check_and_update_ranks(name)
