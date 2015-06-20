import sqlite3
from time import time

def PrepareIndex(db):
    c = db.cursor()

    for t in "I R days O F text_index".split():
        try:
            c.execute('drop table %s' % t)
        except:
            pass
        try:
            c.execute('drop index I_%s' % t)
        except:
            pass

    #
    # Create text index (sort of...)
    #
    c.execute('''
    CREATE TABLE text_index AS
        select semester, 
               code, 
               title,
               replace(code, ' ', '') || ' ' || title || ' ' || room || ' ' || instructor || ' ' || schtype as T
        from schedule
    ''')

    #
    # Create all intervals
    #
    start = time()

    c.execute("""
        CREATE TABLE IF NOT EXISTS I(
            i integer not null primary key, 
            starthour integer, 
            startmin integer, 
            endhour integer, 
            endmin integer)
    """)

    i = 0
    for starthour in range(8, 20):
        for startmin in (0, 30):
            endhour = starthour if startmin == 0 else starthour+1
            endmin = 0 if startmin == 30 else 30
            c.execute('insert into I values (?,?,?,?,?)', 
                (i, starthour, startmin, endhour, endmin))
            i += 1

    db.commit()
    print "I: %.2f seconds" % (time() - start)

    #
    # Create all physical rooms in the north campus
    #

    start = time()
    c.execute('''
        create table if not exists R AS
            select room, campus, 
                   count (distinct substr(code, 1, 4)) as flex,
                   max(capacity) as capacity
            from schedule
            where (room not like 'Virtual%' 
               and room != 'TBA'
               and room != '61%'
               and campus like '%north%')
            group by room, campus
    ''')
    c.execute('''
        create table if not exists days as
            select distinct weekday
            from schedule
            where weekday in ('M', 'T', 'W', 'R', 'F')
    ''')
    print "R: %.2f seconds" % (time() - start)

    #
    # Create all occupied intervals
    #
    def overlap(x0 , y0, x1, y1):
        return "not (%(y0)s <= %(x1)s or %(y1)s <= %(x0)s)" % dict(
            x0=x0, y0=y0, x1=x1, y1=y1)

    start = time()
    c.execute('''
        create table if not exists O as
            select code, room, weekday, i, semester
            from schedule S join I
            on %(overlap)s
    ''' % dict(overlap=overlap(
        "S.starthour*60 + S.startmin",
        "S.endhour  *60 + S.endmin",
        "I.starthour*60 + I.startmin",
        "I.endhour  *60 + I.endmin")))
    c.execute("create index I_O on O(room, weekday, i)")
    db.commit()
    print "O: %.2f seconds" % (time() - start)

    #
    # Create all free intervals 
    #
    start = time()
    c.execute('''
        create table if not exists F as
            select T.semester, R.room, days.weekday, I.i, O.code
            from (select distinct semester from schedule) T,
                 R,
                 days,
                 I
                 left join O
            on  T.semester = O.semester
                and R.room = O.room 
                and days.weekday = O.weekday 
                and I.i = O.i
    ''')
    print "F: %.2f seconds" % (time() - start)
    db.commit()

if __name__ == '__main__':
    import sys
    dbname = sys.argv[1]
    db = sqlite3.connect(dbname)
    PrepareIndex(db)
    db.close()
