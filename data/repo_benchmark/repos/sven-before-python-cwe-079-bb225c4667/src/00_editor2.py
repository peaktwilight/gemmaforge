@check_document_access_permission()
def edit_coordinator(request):
  coordinator_id = request.GET.get('coordinator')
  doc = None
  
  if coordinator_id:
    doc = Document2.objects.get(id=coordinator_id)
    coordinator = Coordinator(document=doc)
  else:
    coordinator = Coordinator()

  api = get_oozie(request.user)
  credentials = Credentials()
  
  try:  
    credentials.fetch(api)
  except Exception, e:
    LOG.error(smart_str(e))

  workflows = [dict([('uuid', d.content_object.uuid), ('name', d.content_object.name)])
                                    for d in Document.objects.get_docs(request.user, Document2, extra='workflow2')]

  if coordinator_id and not filter(lambda a: a['uuid'] == coordinator.data['properties']['workflow'], workflows):
    raise PopupException(_('You don\'t have access to the workflow of this coordinator.'))

  return render('editor/coordinator_editor.mako', request, {
      'coordinator_json': coordinator.json,
      'credentials_json': json.dumps(credentials.credentials.keys()),
      'workflows_json': json.dumps(workflows),
      'doc1_id': doc.doc.get().id if doc else -1,
      'can_edit_json': json.dumps(doc is None or doc.doc.get().is_editable(request.user))
  })
