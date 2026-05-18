    def get_value(self):
        if self.column.render_function:
            # We don't want to escape our html
            return self.column.render_function(self.object)

        field = getattr(self.object, self.column.field_name) if self.column.field_name else None
        if type(self.object) == dict:
            value = self.object.get(self.column.field_name)
        elif callable(field):
            value = field() if getattr(field, 'do_not_call_in_templates', False) else field
        else:
            display_function = getattr(self.object, 'get_%s_display' % self.column.field_name, False)
            value = display_function() if display_function else field

        return escape(value)
