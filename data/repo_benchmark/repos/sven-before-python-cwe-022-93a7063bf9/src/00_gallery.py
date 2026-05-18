async def save(request):
    # TODO csrf
    data = await request.post()
    item = Item(data['src'])

    # Update name
    new_src = data.get('new_src')
    if new_src and new_src != data['src']:
        # don't need to worry about html unquote
        shutil.move(item.abspath, settings.STORAGE_DIR + new_src)
        old_backup_abspath = item.backup_abspath
        item = Item(new_src)
        if os.path.isfile(old_backup_abspath):
            shutil.move(old_backup_abspath, item.backup_abspath)

    # Update meta
    for field in item.FORM:
        # TODO handle .repeatable (keywords)
        item.meta[field] = [data.get(field, '')]

    if settings.SAVE_ORIGINALS and not os.path.isfile(item.backup_abspath):
        shutil.copyfile(item.abspath, item.backup_abspath)

    # WISHLIST don't write() if nothing changed
    item.meta.write()

    return web.Response(
        status=200,
        body=json.dumps(item.get_form_fields()).encode('utf8'),
        content_type='application/json',
    )
