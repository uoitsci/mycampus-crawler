import sqlite3
import sys
from time import time
import re
import math
import itertools

DATA_LIMIT = 5000

def parse_time_to_min(h, m):
    return int(h) * 60 + int(m)

class Row(dict):
    def __init__(self, *E, **F):
        dict.__init__(self, *E, **F)
    def __getattr__(self, name):
        return self[name]

def schedule(dbname, semester, avoid, 
    room=None, weekday=None, campus=None, count=None, flex=None, cap=None,
    after=None, before=None, debug=False):

    if before:
        before = parse_time_to_min(*before.split(":", 1))

    if after:
        after = parse_time_to_min(*after.split(":", 1))

    avoid = parse_avoid(avoid) if avoid else parse_avoid("")

    db = sqlite3.connect(dbname)
    c = db.cursor()

    #
    # gather the intervals taken by the avoids
    #
    sql = 'select weekday, i from O where semester=? and code in (%s)' % ",".join(
        ["?"] * len(avoid))
    param = [semester]
    param.extend(avoid)
    c.execute(sql, param)
    avoid_i = ",".join(["'%s%d'" % x for x in c.fetchall()])

    #
    # get the free intervals
    #
    columns = dict(
        semester='semester',
        weekday='weekday',
        room='room',
        flex='flex',
        capacity='capacity',
        i='I.i'
    )
    sql = '''select %s,
            case when weekday = 'M' then 1
                 when weekday = 'T' then 2
                 when weekday = 'W' then 3
                 when weekday = 'R' then 4
                 when weekday = 'F' then 5
                 else 6
            end as weekday_o
            from F natural join I natural join R
            where code is null
            and semester = ?
            and weekday||i not in (%s)''' % (
                ",".join("%s as %s" % (x[1], x[0]) for x in columns.items()),
                avoid_i)
    param = [semester]

    if room:
        sql += " and room like ?"
        param.append("%%%s%%" % room)
    if weekday:
        sql += " and weekday in (%s)" % ','.join("?" for _ in list(weekday))
        param.extend(list(weekday.upper()))
    if campus:
        sql += " and campus like ?"
        param.append("%%%s%%" % campus)

    if flex:
        sql += " and flex >= ?"
        param.append(int(flex))

    if cap:
        sql += " and capacity >= ?"
        param.append(cap)

    sql += " order by semester, weekday_o, starthour, startmin, room"
    sql += " limit %s" % DATA_LIMIT

    if debug:
        print "avoid:", avoid
        print "sql:", sql, param

    c.execute(sql, param)

    column_names = [x[0] for x in columns.items()]
    answer = [Row(zip(column_names, row)) for row in c.fetchall()]

    #
    # load the I view as a lookup
    #
    sql = '''
        select i, starthour, startmin, endhour, endmin
        from I
    '''
    c.execute(sql)
    I = {}
    for (i, h0, m0, h1, m1) in c.fetchall():
        I[i] = (h0, m0, h1, m1)

    #
    # make sure we have continuity
    #
    slots = set((x.weekday, x.i, x.room) for x in answer)
    feasible_answer = []
    for x in answer:
        y = feasible(x, slots, count)
        if y: 
            y['starthour'] = I[y.i][0]
            y['startmin'] = I[y.i][1]
            y['endhour'] = I[y.j][2]
            y['endmin'] = I[y.j][3]
            y['start'] = "%.2d:%.2d" % (y.starthour, y.startmin)
            y['end'] = "%.2d:%.2d" % (y.endhour, y.endmin)

            if after:
                y_start = parse_time_to_min(y.starthour, y.startmin)
                if not (y_start >= after):
                    continue

            if before:
                y_end = parse_time_to_min(y.endhour, y.endmin)
                if not (y_end <= before):
                    continue

            feasible_answer.append(y)

    db.close()
    return feasible_answer

def feasible(x, slots, n):
    y = Row(x)
    for k in range(n):
        if not (y.weekday, y.i+k, y.room) in slots:
            return None

    # y is the start of a continuous segment spanning n slots.
    y['j'] = y.i + n - 1
    return y

def format_answer(answer):
    lines = []
    for row in answer:
        m = re.match(r'.*\s+(\S+\d+)$', row.room)
        if m: room = m.group(1)
        else: room = row.room
        lines.append("%10s %1s %10s %10s %4d %4d" % (
            row.semester, row.weekday, 
            "%.2d:%.2d-%.2d:%.2d" % (row.starthour, row.startmin, row.endhour, row.endmin), 
            room, row.flex, row.capacity))

    return "\n".join(lines)

def parse_avoid(avoid):
    print "parse_avoid", avoid
    result = []
    for x in avoid.split(","):
        m = re.match(r'([A-Z]+)\s*(\d+)', x.upper())
        if m:
            result.append('%s %sU' % (m.group(1).strip(), m.group(2).strip()))

    print "Result:", result
    return result

def search(dbname, semester, search):
    db = sqlite3.connect(dbname)
    c = db.cursor()
    keywords = re.sub(r'[^ 0-9a-z+]+', ' ', search.lower()).split()
    and_words = [x[1:] for x in keywords if x.startswith('+')]
    or_words = [x for x in keywords if not x.startswith('+')]

    if and_words:
        and_like = " and ".join('T like "%%%s%%"' % x for x in and_words)
    else:
        and_like = None
    if or_words:
        or_like = " or ".join('T like "%%%s%%"' % x for x in or_words)
    else:
        or_like = None

    if and_like and or_like:
        like = and_like + ' and ' + or_like
    elif and_like:
        like = and_like
    elif or_like:
        like = or_like
    else:
        like = '1=1'
    #
    # get the course slots
    #

    columns = dict(
        slot_id = 'weekday||starthour||":"||startmin||":"||endhour||":"||endmin',
        code = 'code',
        title = 'title',
        weekday = 'weekday',
        starthour = 'starthour',
        startmin = 'startmin',
        endhour = 'endhour',
        endmin = 'endmin',
        instructor = 'instructor',
        room = 'room',
        schtype = 'schtype',
        prereq = 'prereq',
        coreq = 'coreq',
        weekday_o = "case when weekday = 'M' then 1 when weekday = 'T' then 2 when weekday = 'W' then 3 when weekday = 'R' then 4 when weekday = 'F' then 5 else 6 end",
    )

    sql = '''
        select distinct %s
        from (select distinct code, semester 
              from text_index where semester=? and (%s) limit 100) T1 
             natural join schedule
        order by weekday_o, starthour, startmin, code
        ''' % (",".join("%s as %s" % (x[1],x[0]) for x in columns.items()), like)
    param = [semester]

    print "sql", sql

    c.execute(sql, param)

    answer = []
    for row in c.fetchall():
        y = Row(zip([x[0] for x in columns.items()], row))
        y['start'] = "%.2d:%.2d" % (y.starthour, y.startmin)
        y['end'] = "%.2d:%.2d" % (y.endhour, y.endmin)
        answer.append(y)
    return answer
    

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Scheduler')
    p.add_argument('--db', dest='dbname')
    p.add_argument('--avoid', dest='avoid')
    p.add_argument('--semester', dest='semester')
    p.add_argument('--room', dest='room')
    p.add_argument('--weekday', dest='weekday')
    p.add_argument('--campus', dest='campus')
    p.add_argument('--duration', dest='duration')
    p.add_argument('--before', dest='before')
    p.add_argument('--after', dest='after')
    p.add_argument('--flex', dest='flex')
    p.add_argument('--debug', dest='debug', action='store_true', default=False)

    args = p.parse_args()
    avoid_string = args.avoid if args.avoid else ""

    if not args.dbname or not args.semester:
        p.print_usage()
        sys.exit()

    if args.duration:
        dur = float(args.duration)
        count = int(math.ceil(dur*60 / 30))
    else:
        count = 1

    answer = schedule(
        dbname = args.dbname, 
        semester = args.semester, 
        avoid = avoid_string, 
        room=args.room,
        campus=args.campus,
        weekday=args.weekday,
        before=args.before,
        after=args.after,
        count=count,
        flex=args.flex,
        debug=args.debug)

    if len(answer) > DATA_LIMIT:
        print "Too many to show: %d" % len(answer)
    else:
        print format_answer(answer)
