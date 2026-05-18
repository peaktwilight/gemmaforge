    def save(self):
        # copy the user's input from plain text to description to be processed
        self.description = self.description_plain_text
        if CE.settings.auto_cross_reference:
            self.auto_cross_ref()
        else:
            self.find_tag()
        self.slug = slugify(self.title)
        super().save()
