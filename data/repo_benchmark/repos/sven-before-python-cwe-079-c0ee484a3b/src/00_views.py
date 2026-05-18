def index(request, is_mobile=False):
  hue_collections = DashboardController(request.user).get_search_collections()
  collection_id = request.GET.get('collection')

  if not hue_collections or not collection_id:
    return admin_collections(request, True, is_mobile)

  try:
    collection_doc = Document2.objects.get(id=collection_id)
    if USE_NEW_EDITOR.get():
      collection_doc.can_read_or_exception(request.user)
    else:
      collection_doc.doc.get().can_read_or_exception(request.user)
    collection = Collection2(request.user, document=collection_doc)
  except Exception, e:
    raise PopupException(e, title=_("Dashboard does not exist or you don't have the permission to access it."))

  query = {'qs': [{'q': ''}], 'fqs': [], 'start': 0}

  if request.method == 'GET':
    if 'q' in request.GET:
      query['qs'][0]['q'] = request.GET.get('q')
    if 'qd' in request.GET:
      query['qd'] = request.GET.get('qd')

  template = 'search.mako'
  if is_mobile:
    template = 'search_m.mako'

  return render(template, request, {
    'collection': collection,
    'query': json.dumps(query),
    'initial': json.dumps({
        'collections': [],
        'layout': DEFAULT_LAYOUT,
        'is_latest': LATEST.get(),
        'engines': get_engines(request.user)
    }),
    'is_owner': collection_doc.doc.get().can_write(request.user),
    'can_edit_index': can_edit_index(request.user),
    'is_embeddable': request.GET.get('is_embeddable', False),
    'mobile': is_mobile,
  })
