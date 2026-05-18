@app.route('/quiz')
def quiz():

    varga = request.args.get('varga')

    try:
        rows =[]

        with sql.connect('amara.db') as con:
            con.row_factory = sql.Row
            cur = con.cursor()
            cur.execute("select * from pada inner join mula on pada.sloka_line = mula.sloka_line where pada.varga = ? order by random() limit 1;", [varga])
            rows = cur.fetchall();

            artha = rows[0]["artha"];
            cur.execute("select pada from pada where varga = ? and artha = ? order by id", [varga, artha]);
            paryaya = cur.fetchall();

            return render_template('quiz.html', rows=rows, paryaya=paryaya, varga=varga)
    finally:
        con.close()
