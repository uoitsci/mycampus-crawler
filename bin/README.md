# How to run it.

## Prerequisite:

- Beautifulsoup 4
- Requests

## Usage

    python dl-to-sqlite.py
        --db <NAME.sqlite3>
        [--semester YYYYMM,YYYYMM,...]
        [--subject CSCI,SOFE,BIOL,...]
        [--loop]

Downloading all of 2015/2016 academic year:

    python dl-to-sqlite.py 
        --db mycampus1516.sqlite3
        --semester 201509,201601

## Database schema

    CREATE TABLE schedule (
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
        );


