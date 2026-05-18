    @staticmethod
    def get_mapped_projects(user_id: int, preferred_locale: str) -> UserMappedProjectsDTO:
        """ Get all projects a user has mapped on """

        # This query looks scary, but we're really just creating an outer join between the query that gets the
        # counts of all mapped tasks and the query that gets counts of all validated tasks.  This is necessary to
        # handle cases where users have only validated tasks on a project, or only mapped on a project.
        sql = '''SELECT p.id,
                        p.status,
                        p.default_locale,
                        c.mapped,
                        c.validated,
                        st_asgeojson(p.centroid)
                   FROM projects p,
                        (SELECT coalesce(v.project_id, m.project_id) project_id,
                                coalesce(v.validated, 0) validated,
                                coalesce(m.mapped, 0) mapped
                          FROM (SELECT t.project_id,
                                       count (t.validated_by) validated
                                  FROM tasks t
                                 WHERE t.project_id IN (SELECT unnest(projects_mapped) FROM users WHERE id = :user_id)
                                   AND t.validated_by = :user_id
                                 GROUP BY t.project_id, t.validated_by) v
                         FULL OUTER JOIN
                        (SELECT t.project_id,
                                count(t.mapped_by) mapped
                           FROM tasks t
                          WHERE t.project_id IN (SELECT unnest(projects_mapped) FROM users WHERE id = :user_id)
                            AND t.mapped_by = :user_id
                          GROUP BY t.project_id, t.mapped_by) m
                         ON v.project_id = m.project_id) c
                   WHERE p.id = c.project_id ORDER BY p.id DESC'''

        results = db.engine.execute(text(sql), user_id=user_id)

        if results.rowcount == 0:
            raise NotFound()

        mapped_projects_dto = UserMappedProjectsDTO()
        for row in results:
            mapped_project = MappedProject()
            mapped_project.project_id = row[0]
            mapped_project.status = ProjectStatus(row[1]).name
            mapped_project.tasks_mapped = row[3]
            mapped_project.tasks_validated = row[4]
            mapped_project.centroid = geojson.loads(row[5])

            project_info = ProjectInfo.get_dto_for_locale(row[0], preferred_locale, row[2])
            mapped_project.name = project_info.name

            mapped_projects_dto.mapped_projects.append(mapped_project)

        return mapped_projects_dto
