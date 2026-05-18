def update_video_positions(removed_position, db):
    db.execute("UPDATE video SET position = position - 1 WHERE position > {removed_position}".format(
        removed_position=removed_position))
