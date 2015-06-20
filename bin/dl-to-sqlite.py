import requests
import re
import sys
import os
import argparse
import index
import shutil
from datetime import datetime

from time import time, sleep
from bs4 import BeautifulSoup, NavigableString

import sqlite3
from datetime import datetime

YEARS = "07 08 09 10 11 12 13 14".split()

def download(semester, subjs):
    all_subjs = [
    'ALSU',
    'AEDT',
    'ANTH',
    'APBS',
    'AUTE',
    'BIOL',
    'BUSI',
    'CHEM',
    'COMM',
    'CDPS',
    'CSCI',
    'ECON',
    'EDUC',
    'ELEE',
    'ENGR',
    'ENGL',
    'ENVS',
    'FSCI',
    'FREN',
    'GEOG',
    'HLSC',
    'HSST',
    'HIST',
    'INFR',
    'LGLS',
    'MANE',
    'MITS',
    'MTSC',
    'MATH',
    'MECE',
    'MLSC',
    'MCSC',
    'NUCL',
    'NURS',
    'PHIL',
    'PHY',
    'POSC',
    'PSYC',
    'RADI',
    'SCIE',
    'SCCO',
    'SSCI',
    'SOCI',
    'SOFE',
    'STAT',
    'WMST',
    ]

    if not subjs: subjs = all_subjs
    subj = "&".join('sel_subj=%s' % x for x in subjs)

    url = "https://ssbp.mycampus.ca/prod/bwckschd.p_get_crse_unsec"
    formdata = """
        TRM=U&term_in=%s&sel_subj=dummy&sel_day=dummy
        &sel_schd=dummy&sel_insm=dummy&sel_camp=dummy
        &sel_levl=dummy&sel_sess=dummy&sel_instr=dummy
        &sel_ptrm=dummy&sel_attr=dummy
        &%s
        &sel_crse=&sel_title=&sel_from_cred=
        &sel_to_cred=&sel_camp=%%25&begin_hh=0
        &begin_mi=0&begin_ap=a&end_hh=0&end_mi=0
        &end_ap=a""" % (semester, subj)

    formdata = "".join([x.strip() for x in formdata.split("\n")]).strip()

    r = requests.post(url, data=formdata)
    return BeautifulSoup(r.text)

def next_sibling(el, name):
    for x in el.next_siblings:
        try:
            if x.name == name:
                return x
        except:
            pass
    return None

def TrList(th):
    trlist = []
    for x in th.next_siblings:
        if not x:
            break
        try:
            if x.name == 'th':
                break
            if x.name == 'tr':
                trlist.append(x)
        except:
            pass

    return trlist

def Info(tr_list, ctx, db):
    #
    # header info
    #
    tr = tr_list[0]
    text = tr.get_text()

    m = re.search(r'UOIT - ([\S ]+)', text)
    if m: ctx.campus = m.group(1).strip()
    else: ctx.campus = None

    m = re.search(r'\s+(\d\.\d+)', text)
    if m: ctx.credits = m.group(1)
    else: ctx.credits = None

    m = re.search(r'Levels: (.*)', text)
    if m: ctx.levels = m.group(1).strip()
    else: ctx.levels = None

    #
    # footer info (prerequisite)
    #
    prerq = []
    coreq = []
    for tr in tr_list[1:]:
        text = tr.get_text()
        m = re.search(r'\*\* PRERQ:(.*)', text)
        if m:
            line = re.sub(r'(\S{4})\s+(\d{4})[^()]*', r'"\1 \2U"', m.group(1).strip())
            prerq.append(line)
        m = re.search(r'\*\* COREQ:(.*)', text)
        if m:
            line = re.sub(r'(\S{4})\s+(\d{4}).*', r'\1 \2U', m.group(1).strip())
            coreq.append(line)

    ctx.prereq = re.sub(r'\s+', ' ', " ".join(prerq)).strip() if prerq else None
    ctx.coreq =  re.sub(r'\s+', ' ', " ".join(coreq)).strip() if coreq else None

def Registration(table, ctx, db):
    seats = table.find_all('td', class_='dbdefault')
    try:
        ctx.cap, ctx.act, ctx.rem = [
            x.get_text().strip() for x in seats[:3]]
    except:
        pass

def Date(x):
    daterange = x.get_text()
    try:
        d0, d1 = daterange.split("-", 1)
        d0, d1 = d0.strip(), d1.strip()
    except Exception, e:
        d0, d1 = None, None
    return (d0, d1)

def DefaultValue(x):
    y = x.get_text().strip()
    return y

Week = Type = Time = Days = Where = SchType = DefaultValue

def Instructor(x):
    v = DefaultValue(x).replace("\n", "")
    return re.sub(r'\(\s*(\S+)\s*\)', '', v)

def Schedule(table, ctx, db):
    entries = list(table.find_all('td', class_='dbdefault'))
    while entries:
        ctx.week    = Week(entries.pop(0))
        ctx.type    = Type(entries.pop(0))
        ctx.time    = Time(entries.pop(0))
        ctx.days    = Days(entries.pop(0))
        ctx.where   = Where(entries.pop(0))
        ctx.date    = Date(entries.pop(0))
        ctx.schtype = SchType(entries.pop(0))
        ctx.inst    = Instructor(entries.pop(0))
        insert(db, ctx)

def Course(th, ctx, db):
    line = th.get_text().strip()
    m = re.match(r'(.*) - (\d+) - (\S+ \d+[A-Z]) - (\d+)', line)
    if m:
        ctx.title   = m.group(1)
        ctx.crn     = m.group(2) 
        ctx.code    = m.group(3)
        ctx.section = m.group(4)
    else:
        pass

class Ctx(dict):
    def __init__(self, *E, **F):
        return dict.__init__(self, *E, **F)
    def __getattr__(self, attr):
        return self[attr]
    def __setattr__(self, attr, val):
        self[attr] = val

    def __str__(self):
        s = " ".join('[%s]"%s"' % (k,v) for k,v in self.items())
        return s

def init_db(db):
    cur = db.cursor()
    #try:
    #    cur.execute("DROP TABLE schedule")
    #except sqlite3.OperationalError:
    #    pass

    cur.execute('create table info (version text)')

    cur.execute('''
        CREATE TABLE if not exists schedule (
            semester    VARCHAR(10),
            title       VARCHAR(100),
            crn         VARCHAR(30),
            code        VARCHAR(30),
            levels      VARCHAR(100),
            credits     FLOAT,
            campus      VARCHAR(50),
            section     INTEGER,
            capacity    INTEGER,
            actual      INTEGER,
            type        VARCHAR(30),
            starthour   INTEGER,
            startmin    INTEGER,
            endhour     INTEGER,
            endmin      INTEGER,
            weekday     VARCHAR(10),
            room        VARCHAR(50),
            datestart   VARCHAR(50),
            dateend     VARCHAR(50),
            schtype     VARCHAR(30),
            instructor  VARCHAR(100),
            prereq      VARCHAR(100),
            coreq       VARCHAR(100)
        )
    ''')
    db.commit()
    return db

def insert(db, ctx):
    title = ctx.title
    crn   = ctx.crn
    code  = ctx.code
    levels = ctx.levels
    try:
        credits = float(ctx.credits)
    except TypeError:
        credits = None
    campus = ctx.campus
    section = int(ctx.section)
    capacity = int(ctx.cap)
    actual = int(ctx.act)
    type_ = ctx.type
    semester = ctx.semester

    starthour, startmin, endhour, endmin = None, None, None, None
    if not ctx.time == 'TBA':
        try:
            start, end = [x.strip() for x in ctx.time.split("-", 1)]
            starttime = datetime.strptime(start, "%I:%M %p")
            endtime   = datetime.strptime(end, "%I:%M %p")
            starthour, startmin = starttime.hour, starttime.minute
            endhour, endmin = endtime.hour, endtime.minute
        except Exception, e:
            print "DATETIME ERROR for", (ctx.time, str(e))
    weekdays = list(ctx.days)
    room = ctx.where
    d0, d1 = ctx.date
    schtype = ctx.schtype
    instructors = [x.strip() for x in ctx.inst.split(",")]
    prereq = ctx.prereq
    coreq = ctx.coreq

    cur = db.cursor()
    for instructor in instructors:
        for weekday in weekdays:
            params = [
                semester,
                title,
                crn,
                code,
                levels,
                credits,
                campus,
                section,
                capacity,
                actual,
                type_,
                starthour,
                startmin,
                endhour,
                endmin,
                weekday,
                room,
                d0,
                d1,
                schtype,
                instructor,
                prereq,
                coreq
            ]
            sql = 'insert into schedule values(%s)' % ",".join(
                "?" for x in range(len(params)))
            cur.execute(sql, params)
            sys.stderr.write(".")

def log(s=""):
    sys.stderr.write(s + "\n")
    sys.stderr.flush()

def main(semester, db, subjs):
    ctx = Ctx()
    ctx.semester = semester
    start = time()
    log("Downloading %s..." % semester)
    soup = download(semester, subjs)
    duration = time() - start
    log("Download completed in %.2f seconds" % duration)

    start = time()
    for th in soup.find_all("th", class_="ddheader"):
        Course(th, ctx, db)
        tr_list = TrList(th)
        
        #
        # General information
        #
        Info(tr_list, ctx, db)

        #
        # Scheduling tables
        #
        tr = tr_list[0]
        for table in tr.find_all('table', class_="bordertable"):
            caption = table.find('caption')
            if caption:
                caption_text = caption.get_text()
                if "Registration" in caption_text:
                    Registration(table, ctx, db)
                if "Scheduled" in caption_text:
                    Schedule(table, ctx, db)
    db.commit()
    log(".")
    duration = time() - start
    log("Created database in %.2f seconds" % duration)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Mycampus Crawler")
    parser.add_argument("--db", dest="dbname")
    parser.add_argument("--semester", dest="semesters")
    parser.add_argument("--subject", dest="subjs")
    parser.add_argument("--loop", dest="loop", help="specify delay in hours")

    args = parser.parse_args()

    if not args.dbname or not args.semesters:
        parser.print_usage()
        sys.exit()
            
    def dl(dbname, args):
        try:
            os.unlink(dbname)
        except:
            pass

        if args.subjs:
            subjs = [x.upper() for x in args.subjs.split(",")]
        else:
            subjs = None

        db = init_db(sqlite3.connect(dbname))

        if args.semesters == 'all':
            semesters = ["20%s%s" % (x,y) for x in YEARS \
                for y in ("09", "01")]
         
        else:
            semesters = args.semesters.split(",")

        for semester in semesters:
            main(semester, db, subjs)

        index.PrepareIndex(db)

        c = db.cursor()
        c.execute('insert into info values(?)', [str(datetime.now())])
        db.commit()
        db.close()

    dbname = args.dbname
    dl(dbname, args)

    while args.loop:
        delay = float(args.loop) * 3600
        print "[%s] Next download in %.2f seconds" % (datetime.now(), delay)
        sleep(delay)
        dl(dbname + "swp", args)
        shutil.move(dbname + "swp", dbname)
