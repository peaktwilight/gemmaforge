def add_article_action(request: HttpRequest, default_foreward_url: str):
    forward_url: str = default_foreward_url
    if request.GET.get("redirect"):
        forward_url = request.GET["redirect"]
    else:
        forward_url = "/admin"
    if "rid" not in request.GET:
        return HttpResponseRedirect("/admin?error=Missing%20reservation%20id%20in%20request")
    u: Profile = get_current_user(request)
    current_reservation = GroupReservation.objects.get(id=str(request.GET["rid"]))
    if current_reservation.createdByUser != u and u.rights < 2:
        return HttpResponseRedirect("/admin?error=noyb")
    if current_reservation.submitted == True:
        return HttpResponseRedirect("/admin?error=Already%20submitted")
    # Test for multiple or single article
    if "article_id" in request.POST:
        # Actual adding of article
        aid: int = int(request.GET.get("article_id"))
        quantity: int = int(request.POST["quantity"])
        notes: str = escape(request.POST["notes"])
        ar = ArticleRequested()
        ar.AID = Article.objects.get(id=aid)
        ar.RID = current_reservation
        if "srid" in request.GET:
            ar.SRID = SubReservation.objects.get(id=int(request.GET["srid"]))
        ar.amount = quantity
        ar.notes = notes
        ar.save()
    # Actual adding of multiple articles
    else:
        if "group_id" not in request.GET:
            return HttpResponseRedirect("/admin?error=missing%20group%20id")
        g: ArticleGroup = ArticleGroup.objects.get(id=int(request.GET["group_id"]))
        for art in Article.objects.all().filter(group=g):
            if str("quantity_" + str(art.id)) not in request.POST or str("notes_" + str(art.id)) not in request.POST:
                return HttpResponseRedirect("/admin?error=Missing%20article%20data%20in%20request")
            amount = int(request.POST["quantity_" + str(art.id)])
            if amount > 0:
                ar = ArticleRequested()
                ar.AID = art
                ar.RID = current_reservation
                ar.amount = amount
                if "srid" in request.GET:
                    ar.SRID = SubReservation.objects.get(id=int(request.GET["srid"]))
                ar.notes = escape(str(request.POST[str("notes_" + str(art.id))]))
                ar.save()
    if "srid" in request.GET:
        response = HttpResponseRedirect(forward_url + "?rid=" + str(current_reservation.id) + "&srid=" + request.GET["srid"])
    else:
        response = HttpResponseRedirect(forward_url + "?rid=" + str(current_reservation.id))
    return response
