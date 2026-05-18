    def save(self):
        # copy the user's input from plain text to description to be processed
        # uses bleach to remove potentially harmful HTML code
        self.description = bleach.clean(str(self.description_plain_text),
                                        tags=CE.settings.bleach_allowed,
                                        strip=True)
        if CE.settings.auto_cross_reference:
            self.auto_cross_ref()
        else:
            self.find_tag()
        self.slug = slugify(self.title)
        super().save()
