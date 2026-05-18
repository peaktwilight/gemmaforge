@app.route('/<page_name>')
def render_page_name(page_name):
    query = db.query("select page_content.content, page.id as page_id, page_content.id as content_id from page, page_content where page.id = page_content.page_id and page.page_name = $1 order by page_content.id desc limit 1", page_name)
    wiki_page = query.namedresult()
    has_content = False
    page_is_taken = False
    if len(wiki_page) < 1:
        content = ""
    else:
        page_is_taken = True
        content = wiki_page[0].content
    if len(content) > 0:
        has_content = True
    else:
        pass
    content = markdown.markdown(wiki_linkify(content))
    return render_template(
        'pageholder.html',
        page_is_taken = page_is_taken,
        page_name = page_name,
        markdown = markdown,
        wiki_linkify = wiki_linkify,
        has_content = has_content,
        content = content
    )
