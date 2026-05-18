    @staticmethod
    def _check_camera_tags(tags):
        """
        Function that convert stupid code name of a smartphone or camera
        from EXIF to meaningful one by looking a collation in a special MySQL
        table For example instead of just Nikon there can be
        NIKON CORPORATION in EXIF

        :param tags: name of a camera and lens from EXIF
        :return: list with one or two strings which are name of
        camera and/or lens. If there is not better name for the gadget
        in database, function just returns name how it is
        """
        checked_tags = []

        for tag in tags:
            if tag:  # If there was this information inside EXIF of the photo
                tag = str(tag).strip()
                log.info('Looking up collation for %s', tag)
                query = ('SELECT right_tag '
                         'FROM tag_table '
                         'WHERE wrong_tag="{}"'.format(tag))
                cursor = db.execute_query(query)
                if not cursor:
                    log.error("Can't check the tag because of the db error")
                    log.warning("Tag will stay as is.")
                    continue
                if cursor.rowcount:
                    # Get appropriate tag from the table
                    tag = cursor.fetchone()[0]
                    log.info('Tag after looking up in tag_tables - %s.', tag)

            checked_tags.append(tag)
        return checked_tags
