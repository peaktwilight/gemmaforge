    def get_context_data(self, *args, **kwargs):
        data = super().get_context_data(*args, **kwargs)

        if self.request.GET.get('back', None) is not None:
            data['back_link'] = self.request.GET['back']

        return data
