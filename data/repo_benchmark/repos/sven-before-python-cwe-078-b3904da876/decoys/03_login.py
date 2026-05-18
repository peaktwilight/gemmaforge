  @handler.unsupported_on_local_server
  @handler.get(handler.HTML)
  def get(self):
    """Handle a get request."""
    dest = self.request.get('dest')
    base_handler.check_redirect_url(dest)

    self.render(
        'login.html', {
            'apiKey': local_config.ProjectConfig().get('firebase.api_key'),
            'authDomain': auth.auth_domain(),
            'dest': dest,
        })
