  @auth.public
  def get(self, build_id):
    try:
      build_id = int(build_id)
    except ValueError:
      self.response.write('invalid build id')
      self.abort(400)

    build = model.Build.get_by_id(build_id)
    can_view = build and user.can_view_build_async(build).get_result()

    if not can_view:
      if auth.get_current_identity().is_anonymous:
        return self.redirect(self.create_login_url(self.request.url))
      self.response.write('build %d not found' % build_id)
      self.abort(404)

    return self.redirect(str(build.url))
