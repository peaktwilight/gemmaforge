    def process_ranks(self, scene, urls, recent_date):
        PLAYER1 = 0
        PLAYER2 = 1
        WINNER = 2
        DATE = 3
        SCENE = 4

        # make sure if we already have calculated ranks for these players at this time, we do not do it again
        sql = "SELECT * FROM ranks WHERE scene = '{}' AND date='{}';".format(str(scene), recent_date)
        res = self.db.exec(sql)
        if len(res) > 0:
            LOG.info('We have already calculated ranks for {} on date {}. SKipping'.format(scene, recent_date))
            return

        matches = bracket_utils.get_matches_from_urls(self.db, urls)
        LOG.info('About to start processing ranks for scene {} on {}'.format(scene, recent_date))

        # Iterate through each match, and build up our dict
        win_loss_dict = {}
        for match in matches:
            p1 = match[PLAYER1]
            p2 = match[PLAYER2]
            winner = match[WINNER]
            date = match[DATE]

            #Add p1 to the dict
            if p1 not in win_loss_dict:
                win_loss_dict[p1] = {}

            if p2 not in win_loss_dict[p1]:
                win_loss_dict[p1][p2] = []

            # Add an entry to represent this match to p1
            win_loss_dict[p1][p2].append((date, winner == p1))

            # add p2 to the dict
            if p2 not in win_loss_dict:
                win_loss_dict[p2] = {}

            if p1 not in win_loss_dict[p2]:
                win_loss_dict[p2][p1] = []

            win_loss_dict[p2][p1].append((date, winner == p2))

        ranks = get_ranks(win_loss_dict)

        tag_rank_map = {}
        for i, x in enumerate(ranks):
            points, player = x
            rank = len(ranks) - i

            sql = "INSERT INTO ranks (scene, player, rank, points, date) VALUES ('{}', '{}', '{}', '{}', '{}');"\
                    .format(str(scene), str(player), int(rank), str(points), str(recent_date))
            self.db.exec(sql)

            # Only count this player if this is the scene he/she belongs to
            sql = "SELECT scene FROM players WHERE tag='{}';".format(player)
            res = self.db.exec(sql)

            if len(res) == 0 or res[0][0] == scene:
                # Also create a list to update the player web
                map = {'rank':rank, 'total_ranked':len(ranks)}
                tag_rank_map[player] = map

        player_web.update_ranks(tag_rank_map)
