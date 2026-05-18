@app.route('/players/<int:player_id>/achievements')
def achievements_list_player(player_id):
    """Lists the progress of achievements for a player.

    :param player_id: ID of the player.

    :return:
        If successful, this method returns a response body with the following structure::

            {
              "items": [
                {
                  "achievement_id": string,
                  "state": string,
                  "current_steps": integer,
                  "create_time": long,
                  "update_time": long
                }
              ]
            }
    """
    with db.connection:
        cursor = db.connection.cursor(db.pymysql.cursors.DictCursor)
        cursor.execute("""SELECT
                            achievement_id,
                            current_steps,
                            state,
                            UNIX_TIMESTAMP(create_time) as create_time,
                            UNIX_TIMESTAMP(update_time) as update_time
                        FROM player_achievements
                        WHERE player_id = %s""", player_id)

        return flask.jsonify(items=cursor.fetchall())
