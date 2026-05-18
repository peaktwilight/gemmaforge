@app.route('/<page_name>/edit')
def render_page_edit(page_name):
    query = db.query("select page_content.content from page, page_content where page.id = page_content.page_id and page.page_name = $1 order by page_content.id desc limit 1", page_name)
    wiki_page = query.namedresult()
    if len(wiki_page) > 0:
        content = wiki_page[0].content
    else:
        content = ""
    return render_template(
        'edit_page.html',
        page_name = page_name,
        content = content
    )
