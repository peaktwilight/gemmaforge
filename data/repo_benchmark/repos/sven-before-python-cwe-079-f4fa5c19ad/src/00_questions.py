    def __init__(self, *args, **kwargs):
        """
        Takes two additional keyword arguments:

        :param cartpos: The cart position the form should be for
        :param event: The event this belongs to
        """
        cartpos = self.cartpos = kwargs.pop('cartpos', None)
        orderpos = self.orderpos = kwargs.pop('orderpos', None)
        pos = cartpos or orderpos
        item = pos.item
        questions = pos.item.questions_to_ask
        event = kwargs.pop('event')

        super().__init__(*args, **kwargs)

        if item.admission and event.settings.attendee_names_asked:
            self.fields['attendee_name_parts'] = NamePartsFormField(
                max_length=255,
                required=event.settings.attendee_names_required,
                scheme=event.settings.name_scheme,
                label=_('Attendee name'),
                initial=(cartpos.attendee_name_parts if cartpos else orderpos.attendee_name_parts),
            )
        if item.admission and event.settings.attendee_emails_asked:
            self.fields['attendee_email'] = forms.EmailField(
                required=event.settings.attendee_emails_required,
                label=_('Attendee email'),
                initial=(cartpos.attendee_email if cartpos else orderpos.attendee_email)
            )

        for q in questions:
            # Do we already have an answer? Provide it as the initial value
            answers = [a for a in pos.answerlist if a.question_id == q.id]
            if answers:
                initial = answers[0]
            else:
                initial = None
            tz = pytz.timezone(event.settings.timezone)
            help_text = rich_text(q.help_text)
            if q.type == Question.TYPE_BOOLEAN:
                if q.required:
                    # For some reason, django-bootstrap3 does not set the required attribute
                    # itself.
                    widget = forms.CheckboxInput(attrs={'required': 'required'})
                else:
                    widget = forms.CheckboxInput()

                if initial:
                    initialbool = (initial.answer == "True")
                else:
                    initialbool = False

                field = forms.BooleanField(
                    label=q.question, required=q.required,
                    help_text=help_text,
                    initial=initialbool, widget=widget,
                )
            elif q.type == Question.TYPE_NUMBER:
                field = forms.DecimalField(
                    label=q.question, required=q.required,
                    help_text=q.help_text,
                    initial=initial.answer if initial else None,
                    min_value=Decimal('0.00'),
                )
            elif q.type == Question.TYPE_STRING:
                field = forms.CharField(
                    label=q.question, required=q.required,
                    help_text=help_text,
                    initial=initial.answer if initial else None,
                )
            elif q.type == Question.TYPE_TEXT:
                field = forms.CharField(
                    label=q.question, required=q.required,
                    help_text=help_text,
                    widget=forms.Textarea,
                    initial=initial.answer if initial else None,
                )
            elif q.type == Question.TYPE_CHOICE:
                field = forms.ModelChoiceField(
                    queryset=q.options,
                    label=q.question, required=q.required,
                    help_text=help_text,
                    widget=forms.Select,
                    empty_label='',
                    initial=initial.options.first() if initial else None,
                )
            elif q.type == Question.TYPE_CHOICE_MULTIPLE:
                field = forms.ModelMultipleChoiceField(
                    queryset=q.options,
                    label=q.question, required=q.required,
                    help_text=help_text,
                    widget=forms.CheckboxSelectMultiple,
                    initial=initial.options.all() if initial else None,
                )
            elif q.type == Question.TYPE_FILE:
                field = forms.FileField(
                    label=q.question, required=q.required,
                    help_text=help_text,
                    initial=initial.file if initial else None,
                    widget=UploadedFileWidget(position=pos, event=event, answer=initial),
                )
            elif q.type == Question.TYPE_DATE:
                field = forms.DateField(
                    label=q.question, required=q.required,
                    help_text=help_text,
                    initial=dateutil.parser.parse(initial.answer).date() if initial and initial.answer else None,
                    widget=DatePickerWidget(),
                )
            elif q.type == Question.TYPE_TIME:
                field = forms.TimeField(
                    label=q.question, required=q.required,
                    help_text=help_text,
                    initial=dateutil.parser.parse(initial.answer).time() if initial and initial.answer else None,
                    widget=TimePickerWidget(time_format=get_format_without_seconds('TIME_INPUT_FORMATS')),
                )
            elif q.type == Question.TYPE_DATETIME:
                field = SplitDateTimeField(
                    label=q.question, required=q.required,
                    help_text=help_text,
                    initial=dateutil.parser.parse(initial.answer).astimezone(tz) if initial and initial.answer else None,
                    widget=SplitDateTimePickerWidget(time_format=get_format_without_seconds('TIME_INPUT_FORMATS')),
                )
            field.question = q
            if answers:
                # Cache the answer object for later use
                field.answer = answers[0]
            self.fields['question_%s' % q.id] = field

        responses = question_form_fields.send(sender=event, position=pos)
        data = pos.meta_info_data
        for r, response in sorted(responses, key=lambda r: str(r[0])):
            for key, value in response.items():
                # We need to be this explicit, since OrderedDict.update does not retain ordering
                self.fields[key] = value
                value.initial = data.get('question_form_data', {}).get(key)
