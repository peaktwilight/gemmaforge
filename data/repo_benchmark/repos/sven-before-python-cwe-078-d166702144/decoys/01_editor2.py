@check_document_access_permission()
def edit_workflow(request):
  workflow_id = request.GET.get('workflow')
  
  if workflow_id:
    wid = {}
    if workflow_id.isdigit():
      wid['id'] = workflow_id
    else:
      wid['uuid'] = workflow_id
    doc = Document2.objects.get(type='oozie-workflow2', **wid)
    workflow = Workflow(document=doc)
  else:
    doc = None
    workflow = Workflow()
    workflow.set_workspace(request.user)
    workflow.check_workspace(request.fs, request.user)
  
  workflow_data = workflow.get_data()

  api = get_oozie(request.user)
  credentials = Credentials()
  
  try:  
    credentials.fetch(api)
  except Exception, e:
    LOG.error(smart_str(e))

  return render('editor/workflow_editor.mako', request, {
      'layout_json': json.dumps(workflow_data['layout'], cls=JSONEncoderForHTML),
      'workflow_json': json.dumps(workflow_data['workflow'], cls=JSONEncoderForHTML),
      'credentials_json': json.dumps(credentials.credentials.keys(), cls=JSONEncoderForHTML),
      'workflow_properties_json': json.dumps(WORKFLOW_NODE_PROPERTIES, cls=JSONEncoderForHTML),
      'doc1_id': doc.doc.get().id if doc else -1,
      'subworkflows_json': json.dumps(_get_workflows(request.user), cls=JSONEncoderForHTML),
      'can_edit_json': json.dumps(doc is None or doc.doc.get().is_editable(request.user))
  })
