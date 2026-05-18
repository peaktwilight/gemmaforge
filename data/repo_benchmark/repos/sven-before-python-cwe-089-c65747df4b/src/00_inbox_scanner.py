def process_as_reply(email_obj):
    job_number = email_obj['subject'].split(': #')[1]
    feedback = re.findall("^[\W]*([Oo\d]){1}(?=[\W]*)", email_obj['content'].replace('#','').replace('link', ''))[0]
    feedback = int(0 if feedback == ('O' or 'o') else feedback)
    dcn_key = re.findall('\w{8}-\w{4}-\w{4}-\w{4}-\w{12}', email_obj['content'])[0]
    logger.info(f"got feedback `{feedback}` for job #`{job_number}`")
    with create_connection() as conn:
        was_prev_closed = pd.read_sql(f"SELECT * FROM df_dilfo WHERE job_number={job_number}", conn).iloc[0].closed
    if was_prev_closed:
        logger.info(f"job was already matched successfully and logged as `closed`... skipping.")
        return
    if feedback == 1:
        logger.info(f"got feeback that DCN key {dcn_key} was correct")
        update_status_query = "UPDATE df_dilfo SET closed = 1 WHERE job_number = {}"
        with create_connection() as conn:
            conn.cursor().execute(update_status_query.format(job_number))
        logger.info(f"updated df_dilfo to show `closed` status for job #{job_number}")
    with create_connection() as conn:
        df = pd.read_sql("SELECT * FROM df_matched", conn)
        match_dict_input = {
            'job_number': job_number,
            'dcn_key': dcn_key,
            'ground_truth': 1 if feedback == 1 else 0,
            'multi_phase': 1 if feedback == 2 else 0,
            'verifier': email_obj["sender"],
            'source': 'feedback',
            'log_date': str(datetime.datetime.now().date()),
            'validate': 0,
        }
        df = df.append(match_dict_input, ignore_index=True)
        df = df.drop_duplicates(subset=["job_number", "dcn_key"], keep='last')
        df.to_sql('df_matched', conn, if_exists='replace', index=False)
        logger.info(
            f"DCN key `{dcn_key}` was a "
            f"{'successful match' if feedback == 1 else 'mis-match'} for job "
            f"#{job_number}"
        )
