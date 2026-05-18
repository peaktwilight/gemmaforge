    def system_search(self, search):
        search = search.lower()
        conn = sqlite3.connect('data/ed.db').cursor()
        table = conn.execute('select * from populated where lower(name) = ?', (search,))
        results = table.fetchone()
        if not results:
            table = conn.execute('select * from systems where lower(name) = ?', (search,))
            results = table.fetchone()
        if results:
            keys = tuple(i[0] for i in table.description) 
            return '\n'.join(f'{key.replace("_", " ").title()}: {field}'
                             for key, field in zip(keys[1:], results[1:]) if field)
        else:
            return 'No systems found.'
