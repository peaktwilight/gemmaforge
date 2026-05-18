  def redirect(self, url, **kwargs):
    """Explicitly converts url to 'str', because webapp2.RequestHandler.redirect
    strongly requires 'str' but url might be an unicode string."""
    url = str(url)
    check_redirect_url(url)
    super(Handler, self).redirect(url, **kwargs)
