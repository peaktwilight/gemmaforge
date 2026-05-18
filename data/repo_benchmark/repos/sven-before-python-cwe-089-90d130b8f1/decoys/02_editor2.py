@check_document_access_permission()
def edit_bundle(request):
  bundle_id = request.GET.get('bundle')
  doc = None
  
  if bundle_id:
    doc = Document2.objects.get(id=bundle_id)
    bundle = Bundle(document=doc)
  else:
    bundle = Bundle()

  coordinators = [dict([('uuid', d.content_object.uuid), ('name', d.content_object.name)])
                      for d in Document.objects.get_docs(request.user, Document2, extra='coordinator2')]

  return render('editor/bundle_editor.mako', request, {
      'bundle_json': bundle.json_for_html(),
      'coordinators_json': json.dumps(coordinators, cls=JSONEncoderForHTML),
      'doc1_id': doc.doc.get().id if doc else -1,
      'can_edit_json': json.dumps(doc is None or doc.doc.get().is_editable(request.user))      
  })
