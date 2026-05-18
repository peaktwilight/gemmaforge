    @staticmethod
    def auto_unlock_tasks(project_id: int):
        """Unlock all tasks locked for longer than the auto-unlock delta"""
        expiry_delta = Task.auto_unlock_delta()
        lock_duration = (datetime.datetime.min + expiry_delta).time().isoformat()
        expiry_date = datetime.datetime.utcnow() - expiry_delta
        old_locks_query = '''SELECT t.id
            FROM tasks t, task_history th
            WHERE t.id = th.task_id
            AND t.project_id = th.project_id
            AND t.task_status IN (1,3)
            AND th.action IN ( 'LOCKED_FOR_VALIDATION','LOCKED_FOR_MAPPING' )
            AND th.action_text IS NULL
            AND t.project_id = {0}
            AND th.action_date <= '{1}'
            '''.format(project_id, str(expiry_date))

        old_tasks = db.engine.execute(old_locks_query)

        if old_tasks.rowcount == 0:
            # no tasks older than the delta found, return without further processing
            return

        for old_task in old_tasks:
            task = Task.get(old_task[0], project_id)
            task.auto_unlock_expired_tasks(expiry_date, lock_duration)
