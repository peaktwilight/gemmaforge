def list_editor_workflows(request):  
  workflows = [d.content_object.to_dict() for d in Document.objects.get_docs(request.user, Document2, extra='workflow2')]

  return render('editor/list_editor_workflows.mako', request, {
      'workflows_json': json.dumps(workflows)
  })
