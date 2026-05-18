@app.route('/sloka')
def sloka():

    sloka_number = request.args.get('sloka_number')

    sloka_number_parts = sloka_number.split('.')

    sloka_number_previous = "%s.%s.%d" % (sloka_number_parts[0], sloka_number_parts[1], int(sloka_number_parts[2])-1)
    sloka_number_next = "%s.%s.%d" % (sloka_number_parts[0], sloka_number_parts[1], int(sloka_number_parts[2])+1)

    try:
        with sql.connect('amara.db') as con:
            con.row_factory = sql.Row
            cur = con.cursor()
            cur.execute("select * from mula where sloka_number = '%s' order by sloka_line;" % sloka_number)
            mula = cur.fetchall();

            cur.execute("select * from pada where sloka_number = '%s' order by id;" % sloka_number)
            pada = cur.fetchall();

            varga = ""
            if len(pada) > 0:
                varga = pada[0]["varga"]

            return render_template('sloka.html', mula=mula, pada=pada, varga=varga, sloka_number=sloka_number, sloka_number_previous=sloka_number_previous, sloka_number_next=sloka_number_next)
    finally:
        con.close()
