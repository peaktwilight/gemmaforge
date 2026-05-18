    def get_value(self):
        field = getattr(self.object, self.column.field_name) if self.column.field_name else None
        if self.column.render_function:
            template = self.column.render_function(self.object)
            if not self.is_template_instance(template):
                raise SmartListException(
                    'Your render_function {} should return django.template.Template or django.template.backends.django.Template object instead of {}'.format(
                        self.column.render_function.__name__,
                        type(template),
                    )
                )
            value = template.render()
        elif type(self.object) == dict:
            value = self.object.get(self.column.field_name)
        elif callable(field):
            value = field() if getattr(field, 'do_not_call_in_templates', False) else field
        else:
            display_function = getattr(self.object, 'get_%s_display' % self.column.field_name, False)
            value = display_function() if display_function else field

        return value
