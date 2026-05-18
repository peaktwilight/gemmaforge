    @property
    async def html_content(self):
        content = await self.content
        if not content:
            return ''
        return markdown(content)
