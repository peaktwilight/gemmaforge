def manipulate_reservation_action(request: HttpRequest, default_foreward_url: str):
    """
    This function is used to alter the reservation beeing build inside
    a cookie. This function automatically crafts the required response.
    """
    js_string: str = ""
    r: GroupReservation = None
    u: Profile = get_current_user(request)
    forward_url: str = default_foreward_url
    if request.GET.get("redirect"):
        forward_url = request.GET["redirect"]
    if "srid" in request.GET:
        if not request.GET.get("rid"):
            return HttpResponseRedirect("/admin?error=missing%20primary%20reservation%20id")
        srid: int = int(request.GET["srid"])
        sr: SubReservation = None
        if srid == 0:
            sr = SubReservation()
        else:
            sr = SubReservation.objects.get(id=srid)
        if request.POST.get("notes"):
            sr.notes = request.POST["notes"]
        else:
            sr.notes = " "
        sr.primary_reservation = GroupReservation.objects.get(id=int(request.GET["rid"]))
        sr.save()
        print(request.POST)
        print(sr.notes)
        return HttpResponseRedirect("/admin/reservations/edit?rid=" + str(int(request.GET["rid"])) + "&srid=" + str(sr.id))
    if "rid" in request.GET:
        # update reservation
        r = GroupReservation.objects.get(id=int(request.GET["rid"]))
    elif u.number_of_allowed_reservations > GroupReservation.objects.all().filter(createdByUser=u).count():
        r = GroupReservation()
        r.createdByUser = u
        r.ready = False
        r.open = True
        r.pickupDate = datetime.datetime.now()
    else:
        return HttpResponseRedirect("/admin?error=Too%20Many%20reservations")
    if request.POST.get("notes"):
        r.notes = request.POST["notes"]
    if request.POST.get("contact"):
        r.responsiblePerson = str(request.POST["contact"])
    if (r.createdByUser == u or o.rights > 1) and not r.submitted:
        r.save()
    else:
        return HttpResponseRedirect("/admin?error=noyb")
    response: HttpResponseRedirect = HttpResponseRedirect(forward_url + "?rid=" + str(r.id))
    return response
