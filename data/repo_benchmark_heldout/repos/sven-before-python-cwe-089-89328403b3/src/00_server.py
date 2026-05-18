@app.route('/<page_name>/history/record')
def view_page_record(page_name):
    content_id = request.args.get('id')
    query = db.query("select page_content.content, page_content.timestamp from page, page_content where page.id = page_content.page_id and page_content.id = '%s'" % content_id)
    page_record = query.namedresult()[0]

    return render_template(
        'page_record.html',
        page_name = page_name,
        page_record = page_record
    )
