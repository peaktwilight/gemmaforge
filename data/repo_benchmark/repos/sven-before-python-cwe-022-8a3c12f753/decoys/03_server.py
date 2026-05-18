@app.route('/<page_name>/history')
def view_page_history(page_name):
    query = db.query("select page_content.timestamp, page_content.id from page, page_content where page.id = page_content.page_id and page.page_name = $1", page_name)
    page_histories = query.namedresult()

    return render_template(
        'page_history.html',
        page_name = page_name,
        page_histories = page_histories
    )
