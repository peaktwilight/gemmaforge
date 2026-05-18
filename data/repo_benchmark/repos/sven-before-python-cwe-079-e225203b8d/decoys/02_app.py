    def get(self, path):
        path = self.sanitize_path(path)
        base_paths = self.get_base_paths()
        if hasattr(base_paths, 'split'):
            # String, so go simple
            base_path = base_paths
        else:
            base_path = self.get_first_base(base_paths, path)
        return static_file(path, base_path)
