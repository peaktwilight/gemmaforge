    @staticmethod
    def estimate_size(task_id, taken_dirs, taken_files):
        report = AnalysisController.get_report(task_id)
        report = report["analysis"]
        path = report["info"]["analysis_path"]

        size_total = 0

        for directory in taken_dirs:
            destination = "%s/%s" % (path, directory)
            if os.path.isdir(destination):
                size_total += get_directory_size(destination)

        for filename in taken_files:
            destination = "%s/%s" % (path, filename)
            if os.path.isfile(destination):
                size_total += os.path.getsize(destination)

        # estimate file size after zipping; 60% compression rate typically
        size_estimated = size_total / 6.5

        return {
            "size": int(size_estimated),
            "size_human": filesizeformat(size_estimated)
        }
