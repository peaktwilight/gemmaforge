@app.route("/<page_name>/edit")
def edit_page(page_name):
    query = db.query("select * from page where title = $1", page_name).namedresult()
    if len(query) == 0:
        return render_template(
            "edit.html",
            page_name=page_name,
            query=query
        )
    else:
        return render_template(
            "edit.html",
            page_name=page_name,
            query=query[0]
        )
