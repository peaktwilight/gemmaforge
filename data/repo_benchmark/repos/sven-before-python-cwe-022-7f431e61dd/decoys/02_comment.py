    @property
    async def html_content(self):
        content = markupsafe.escape(await self.content)
        if not content:
            return ''
        return markdown(content)
