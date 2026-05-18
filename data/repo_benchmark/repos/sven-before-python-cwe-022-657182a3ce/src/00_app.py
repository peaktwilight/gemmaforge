    def get(self, path):
        return static_file(path, self.get_base_path())
