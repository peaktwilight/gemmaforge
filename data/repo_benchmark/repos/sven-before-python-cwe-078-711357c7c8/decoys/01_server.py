@app.route("/search", methods = ["POST"])
def search_pages():
    search = request.form.get("search")
    page = db.query("select title from page where title = $1", search).namedresult()
    if len(page) == 0:
        return redirect("/%s" % search)
    else:
        return place_holder(search)
