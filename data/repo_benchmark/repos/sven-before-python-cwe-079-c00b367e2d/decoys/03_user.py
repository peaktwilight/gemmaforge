    @staticmethod
    def upsert_mapped_projects(user_id: int, project_id: int):
        """ Adds projects to mapped_projects if it doesn't exist """
        sql = "select * from users where id = :user_id and projects_mapped @> '{{:project_id}}'"
        result = db.engine.execute(text(sql), user_id=user_id, project_id=project_id)

        if result.rowcount > 0:
            return  # User has previously mapped this project so return

        sql = '''update users
                    set projects_mapped = array_append(projects_mapped, :project_id)
                  where id = :user_id'''

        db.engine.execute(text(sql), project_id=project_id, user_id=user_id)
