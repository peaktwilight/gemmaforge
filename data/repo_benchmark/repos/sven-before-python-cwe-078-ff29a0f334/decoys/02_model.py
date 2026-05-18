def get_mod_taken_together_with(code):
    '''
        Retrieves the list of modules taken together with the specified
        module code in the same semester.

        Returns a table of lists (up to 10 top results). Each list contains
        (specified code, module code of mod taken together, aySem, number of students)

        e.g. [(CS1010, CS1231, AY 16/17 Sem 1, 5)] means there are 5 students
        taking CS1010 and CS1231 together in AY 16/17 Sem 1.
    '''
    NUM_TOP_RESULTS_TO_RETURN = 10

    sql_command = "SELECT sp1.moduleCode, sp2.moduleCode, sp1.acadYearAndSem, COUNT(*) " + \
                "FROM studentPlans sp1, studentPlans sp2 " + \
                "WHERE sp1.moduleCode = %s AND " + \
                "sp2.moduleCode <> sp1.moduleCode AND " + \
                "sp1.studentId = sp2.studentId AND " + \
                "sp1.acadYearAndSem = sp2.acadYearAndSem " + \
                "GROUP BY sp1.moduleCode, sp2.moduleCode, sp1.acadYearAndSem " + \
                "ORDER BY COUNT(*) DESC"

    DB_CURSOR.execute(sql_command, (code,))

    return DB_CURSOR.fetchmany(NUM_TOP_RESULTS_TO_RETURN)
