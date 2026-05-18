def action_save_user(request: HttpRequest, default_forward_url: str = "/admin/users"):
    """
    This functions saves the changes to the user or adds a new one. It completely creates the HttpResponse
    :param request: the HttpRequest
    :param default_forward_url: The URL to forward to if nothing was specified
    :return: The crafted HttpResponse
    """
    forward_url = default_forward_url
    if request.GET.get("redirect"):
        forward_url = request.GET["redirect"]
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    profile = Profile.objects.get(authuser=request.user)
    if profile.rights < 2:
        return HttpResponseForbidden()
    try:
        if request.GET.get("user_id"):
            pid = int(request.GET["user_id"])
            displayname = str(request.POST["display_name"])
            dect = int(request.POST["dect"])
            notes = str(request.POST["notes"])
            pw1 = str(request.POST["password"])
            pw2 = str(request.POST["confirm_password"])
            mail = str(request.POST["email"])
            rights = int(request.POST["rights"])
            user: Profile = Profile.objects.get(pk=pid)
            user.displayName = displayname
            user.dect = dect
            user.notes = notes
            user.rights = rights
            user.number_of_allowed_reservations = int(request.POST["allowed_reservations"])
            if request.POST.get("active"):
                user.active = magic.parse_bool(request.POST["active"])
            au: User = user.authuser
            if check_password_conformity(pw1, pw2):
                logging.log(logging.INFO, "Set password for user: " + user.displayName)
                au.set_password(pw1)
            else:
                logging.log(logging.INFO, "Failed to set password for: " + user.displayName)
            au.email = mail
            au.save()
            user.save()
        else:
            # assume new user
            username = str(request.POST["username"])
            displayname = str(request.POST["display_name"])
            dect = int(request.POST["dect"])
            notes = str(request.POST["notes"])
            pw1 = str(request.POST["password"])
            pw2 = str(request.POST["confirm_password"])
            mail = str(request.POST["email"])
            rights = int(request.POST["rights"])
            if not check_password_conformity(pw1, pw2):
                recreate_form('password mismatch')
            auth_user: User = User.objects.create_user(username=username, email=mail, password=pw1)
            auth_user.save()
            user: Profile = Profile()
            user.rights = rights
            user.number_of_allowed_reservations = int(request.POST["allowed_reservations"])
            user.displayName = displayname
            user.authuser = auth_user
            user.dect = dect
            user.notes = notes
            user.active = True
            user.save()
            pass
        pass
    except Exception as e:
        return HttpResponseBadRequest(str(e))
    return redirect(forward_url)
