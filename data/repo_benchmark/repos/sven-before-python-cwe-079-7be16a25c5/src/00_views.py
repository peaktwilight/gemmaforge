@login_required(redirect_field_name='', login_url='/403')
@require_POST
@require_AJAX
@transaction.atomic
def batch_edit_translations(request):
    """Perform an action on a list of translations.

    Available actions are defined in `ACTIONS_FN_MAP`. Arguments to this view
    are defined in `models.BatchActionsForm`.

    """
    form = forms.BatchActionsForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json())

    locale = get_object_or_404(Locale, code=form.cleaned_data['locale'])
    entities = Entity.objects.filter(pk__in=form.cleaned_data['entities'])

    if not entities.exists():
        return JsonResponse({'count': 0})

    # Batch editing is only available to translators. Check if user has
    # translate permissions for all of the projects in passed entities.
    # Also make sure projects are not enabled in read-only mode for a locale.
    projects_pk = entities.values_list('resource__project__pk', flat=True)
    projects = Project.objects.filter(pk__in=projects_pk.distinct())

    for project in projects:
        if (
            not request.user.can_translate(project=project, locale=locale)
            or readonly_exists(projects, locale)
        ):
            return HttpResponseForbidden(
                "Forbidden: You don't have permission for batch editing"
            )

    # Find all impacted active translations, including plural forms.
    active_translations = Translation.objects.filter(
        active=True,
        locale=locale,
        entity__in=entities,
    )

    # Execute the actual action.
    action_function = ACTIONS_FN_MAP[form.cleaned_data['action']]
    action_status = action_function(
        form,
        request.user,
        active_translations,
        locale,
    )

    if action_status.get('error'):
        return JsonResponse(action_status)

    invalid_translation_count = len(action_status.get('invalid_translation_pks', []))
    if action_status['count'] == 0:
        return JsonResponse({
            'count': 0,
            'invalid_translation_count': invalid_translation_count,
        })

    update_stats(action_status['translated_resources'], locale)
    mark_changed_translation(action_status['changed_entities'], locale)

    # Update latest translation.
    if action_status['latest_translation_pk']:
        Translation.objects.get(
            pk=action_status['latest_translation_pk']
        ).update_latest_translation()

    update_translation_memory(
        action_status['changed_translation_pks'],
        project,
        locale
    )

    return JsonResponse({
        'count': action_status['count'],
        'invalid_translation_count': invalid_translation_count,
    })
