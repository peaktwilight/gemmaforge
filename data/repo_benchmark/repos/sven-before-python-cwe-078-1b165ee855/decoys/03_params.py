    def add_extra_args(self, args=None):
        """Add more args depending on how known args are set."""
        parsed = vars(self.parse_known_args(args, nohelp=True)[0])

        # find which image mode specified if any, and add additional arguments
        image_mode = parsed.get('image_mode', None)
        if image_mode is not None and image_mode != 'none':
            self.add_image_args(image_mode)

        # find which task specified if any, and add its specific arguments
        task = parsed.get('task', None)
        if task is not None:
            self.add_task_args(task)
        evaltask = parsed.get('evaltask', None)
        if evaltask is not None:
            self.add_task_args(evaltask)

        # find which model specified if any, and add its specific arguments
        model = parsed.get('model', None)
        if model is not None:
            self.add_model_subargs(model)

        # reset parser-level defaults over any model-level defaults
        try:
            self.set_defaults(**self._defaults)
        except AttributeError:
            raise RuntimeError('Please file an issue on github that argparse '
                               'got an attribute error when parsing.')
