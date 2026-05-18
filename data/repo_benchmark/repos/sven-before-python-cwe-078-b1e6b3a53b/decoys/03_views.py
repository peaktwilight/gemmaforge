    def get_context_data(self, *args, **kwargs):
        data = super().get_context_data(*args, **kwargs)

        back = self.request.GET.get('back', None)
        parsed_back_url = urllib.parse.urlparse(back)

        # We only allow blank scheme, e.g. relative urls to avoid reflected XSS
        if back is not None and parsed_back_url.scheme == "":
            data['back_link'] = back

        return data
