    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comment_set.all().order_by('-time')
        context['form'] = self.get_form()
        context['md'] = safe_md(self.object.content)

        return context
