    @classmethod
    def simple_search(cls, query, using=None, index=None):
        es_search = cls.search(using=using, index=index)
        es_query = cls.get_es_query(query=query)
        highlighted_fields = [f.split('^', 1)[0] for f in cls.search_fields]

        es_search = es_search.query(es_query).highlight(*highlighted_fields)
        return es_search
