    @staticmethod
    def get_max_task_id_for_project(project_id: int):
        """Gets the nights task id currently in use on a project"""
        sql = """select max(id) from tasks where project_id = :project_id GROUP BY project_id"""
        result = db.engine.execute(text(sql), project_id=project_id)
        if result.rowcount == 0:
            raise NotFound()
        for row in result:
            return row[0]
