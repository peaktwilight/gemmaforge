    @classmethod
    def simple_search(cls, query, using=None, index=None):
        """
        Do a search without facets.

        This is used in:

        * The Docsearch API
        * The Project Admin Search page
        """

        es_search = cls.search(using=using, index=index)
        es_search = es_search.highlight_options(encoder='html')

        es_query = cls.get_es_query(query=query)
        highlighted_fields = [f.split('^', 1)[0] for f in cls.search_fields]
        es_search = es_search.query(es_query).highlight(*highlighted_fields)

        return es_search
