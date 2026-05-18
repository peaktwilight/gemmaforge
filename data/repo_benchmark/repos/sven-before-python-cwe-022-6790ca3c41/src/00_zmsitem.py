    def zmi_page_request(self, *args, **kwargs):
      request = self.REQUEST
      RESPONSE = request.RESPONSE
      SESSION = request.SESSION
      self._zmi_page_request()
      RESPONSE.setHeader('Expires',DateTime(request['ZMI_TIME']-10000).toZone('GMT+1').rfc822())
      RESPONSE.setHeader('Cache-Control', 'no-cache')
      RESPONSE.setHeader('Pragma', 'no-cache')
      RESPONSE.setHeader('Content-Type', 'text/html;charset=%s'%request['ZMS_CHARSET'])
      if not request.get( 'preview'):
        request.set( 'preview','preview')
      langs = self.getLanguages(request)
      if request.get('lang') not in langs:
        request.set('lang',langs[0])
      if request.get('manage_lang') not in self.getLocale().get_manage_langs():
        request.set('manage_lang',self.get_manage_lang())
      if not request.get('manage_tabs_message'):
        request.set( 'manage_tabs_message',self.getConfProperty('ZMS.manage_tabs_message',''))
      # manage_system
      if request.form.has_key('zmi-manage-system'):
        request.SESSION.set('zmi-manage-system',int(request.get('zmi-manage-system')))
      # avoid declarative urls
      physical_path = self.getPhysicalPath()
      path_to_handle = request['URL0'][len(request['BASE0']):].split('/')
      path = path_to_handle[:-1]
      if len(filter(lambda x:x.find('.')>0 or x.startswith('manage_'),path))==0:
        for i in range(len(path)):
          if path[:-(i+1)] != physical_path[:-(i+1)]:
            path[:-(i+1)] = physical_path[:-(i+1)]
        new_path = path+[path_to_handle[-1]]
        if path_to_handle != new_path:
          request.RESPONSE.redirect('/'.join(new_path))
