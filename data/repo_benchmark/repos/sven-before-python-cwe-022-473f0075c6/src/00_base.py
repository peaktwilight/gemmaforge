    def candidate_paths_for_url(self, url):
        for root, prefix in self.directories:
            if url.startswith(prefix):
                yield os.path.join(root, url[len(prefix):])
