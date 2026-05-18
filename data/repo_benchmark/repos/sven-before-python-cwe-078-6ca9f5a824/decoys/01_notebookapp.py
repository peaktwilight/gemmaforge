    def init_settings(self, ipython_app, kernel_manager, contents_manager,
                      cluster_manager, session_manager, kernel_spec_manager,
                      config_manager,
                      log, base_url, default_url, settings_overrides,
                      jinja_env_options=None):

        _template_path = settings_overrides.get(
            "template_path",
            ipython_app.template_file_path,
        )
        if isinstance(_template_path, py3compat.string_types):
            _template_path = (_template_path,)
        template_path = [os.path.expanduser(path) for path in _template_path]

        jenv_opt = {"autoescape": True}
        jenv_opt.update(jinja_env_options if jinja_env_options else {})

        env = Environment(loader=FileSystemLoader(template_path), **jenv_opt)
        
        sys_info = get_sys_info()
        if sys_info['commit_source'] == 'repository':
            # don't cache (rely on 304) when working from master
            version_hash = ''
        else:
            # reset the cache on server restart
            version_hash = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        settings = dict(
            # basics
            log_function=log_request,
            base_url=base_url,
            default_url=default_url,
            template_path=template_path,
            static_path=ipython_app.static_file_path,
            static_handler_class = FileFindHandler,
            static_url_prefix = url_path_join(base_url,'/static/'),
            static_handler_args = {
                # don't cache custom.js
                'no_cache_paths': [url_path_join(base_url, 'static', 'custom')],
            },
            version_hash=version_hash,
            
            # authentication
            cookie_secret=ipython_app.cookie_secret,
            login_url=url_path_join(base_url,'/login'),
            login_handler_class=ipython_app.login_handler_class,
            logout_handler_class=ipython_app.logout_handler_class,
            password=ipython_app.password,

            # managers
            kernel_manager=kernel_manager,
            contents_manager=contents_manager,
            cluster_manager=cluster_manager,
            session_manager=session_manager,
            kernel_spec_manager=kernel_spec_manager,
            config_manager=config_manager,

            # IPython stuff
            jinja_template_vars=ipython_app.jinja_template_vars,
            nbextensions_path=ipython_app.nbextensions_path,
            websocket_url=ipython_app.websocket_url,
            mathjax_url=ipython_app.mathjax_url,
            config=ipython_app.config,
            jinja2_env=env,
            terminals_available=False,  # Set later if terminals are available
        )

        # allow custom overrides for the tornado web app.
        settings.update(settings_overrides)
        return settings
