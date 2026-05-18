def nav_path(request):
  """Return current path as list of items with "name" and "href" members

  The href members are view_directory links for directories and view_log
  links for files, but are set to None when the link would point to
  the current view"""

  if not request.repos:
    return []

  is_dir = request.pathtype == vclib.DIR

  # add root item
  items = []
  root_item = _item(name=request.server.escape(request.repos.name), href=None)
  if request.path_parts or request.view_func is not view_directory:
    root_item.href = request.get_url(view_func=view_directory,
                                     where='', pathtype=vclib.DIR,
                                     params={}, escape=1)
  items.append(root_item)

  # add path part items
  path_parts = []
  for part in request.path_parts:
    path_parts.append(part)
    is_last = len(path_parts) == len(request.path_parts)

    item = _item(name=part, href=None)

    if not is_last or (is_dir and request.view_func is not view_directory):
      item.href = request.get_url(view_func=view_directory,
                                  where=_path_join(path_parts),
                                  pathtype=vclib.DIR,
                                  params={}, escape=1)
    elif not is_dir and request.view_func is not view_log:
      item.href = request.get_url(view_func=view_log,
                                  where=_path_join(path_parts),
                                  pathtype=vclib.FILE,
                                  params={}, escape=1)
    items.append(item)

  return items
