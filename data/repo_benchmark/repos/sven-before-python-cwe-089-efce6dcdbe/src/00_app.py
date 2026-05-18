@app.route('/movies/add', methods=['GET', 'POST'])
def add_movie():
    form = MovieForm()
    if not form.validate_on_submit():
        return render_template('new_movie.html', title='Add New Movie', form=form)
    lang_id = add_language(form.data['language'])
    movie = {
            'title': '',
            'description': '',
            'release_year': 0,
            'rental_duration': 0,
            'rental_rate': 0.00,
            'length': 0,
            'replacement_cost': 0.00
        }
    for k, v in movie.items():
        movie[k] = form.data[k]
    movie['language_id'] = movie.get('language_id', lang_id)
    cur.execute(
        """
        INSERT INTO film (title, description, release_year, language_id, rental_duration, rental_rate, length, replacement_cost)
        VALUES ('{}', '{}', {}, {}, {}, {}, {}, {})
        """.format(*[v for k, v in movie.items()])
    )
    try:
        cur.execute(f"SELECT * FROM film where fulltext @@ to_tsquery('Dark Knight')")
        res = cur.fetchall()
        conn.commit()
        return redirect(url_for('movies'))
    except Exception as e:
        return redirect(url_for('index'))
