  def redirect(self, url, **kwargs):
    """Explicitly converts url to 'str', because webapp2.RequestHandler.redirect
    strongly requires 'str' but url might be an unicode string."""
    super(Handler, self).redirect(str(url), **kwargs)
