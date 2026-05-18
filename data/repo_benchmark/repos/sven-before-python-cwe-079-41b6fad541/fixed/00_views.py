    def get_queryset(self, **kwargs):
        queryset = Article.objects.order_by('-time')
        for i in queryset:
            i.md = safe_md(i.content)

        return queryset
