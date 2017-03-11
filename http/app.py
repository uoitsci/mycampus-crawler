from flask import Flask, request, redirect, url_for, render_template
import flask
import schedule
from time import time
import re
import sqlite3
import os

app = Flask(__name__)

dbname = os.getenv("DBNAME", "/data/a.sqlite3")

@app.route("/")
def Index():
    return render_template('Index.html') 

@app.route("/free")
def Free():
    return render_template('Free.html') 

@app.route("/search")
def search():
    return render_template('Search.html') 

@app.route("/q/free")
def QueryFree():
    semester = request.args.get('semester', None)
    avoid = request.args.get('avoid', '')
    room = request.args.get('room', '')
    campus = request.args.get('campus', '')
    weekday = request.args.get('weekday', '')
    duration = request.args.get('duration', '1')
    flex = request.args.get('flex', 1)
    cap = request.args.get('cap', 1)

    start = time()

    if not semester:
        return flask.jsonify({
            'error': 'Semester is missing.',
             'duration': "%.2f" % (time()-start)
        })

    try:
        duration = int(float(duration) * 2)
        flex = int(flex)
        cap = int(cap)
    except:
        return flask.jsonify(dict(error="Duration/Flex/Cap is invalid."))

    answer = schedule.schedule(dbname = dbname,
        semester = semester,
        avoid = avoid,
        room = room,
        campus = campus,
        weekday = weekday,
        count = duration,
        flex = flex,
        cap = cap)

    if len(answer) > 1000:
        return flask.jsonify(
            dict(error="Too many solutions: %d found." % len(answer),
                 duration="%.2f" % (time()-start)))

    return flask.jsonify({
        'total': len(answer),
        'data': answer,
        'duration': "%.2f" % (time()-start)
    })

@app.route("/q/info")
def Info():
    db = sqlite3.connect(dbname)
    c = db.cursor()
    c.execute('select max(version) from info')
    results = c.fetchall()
    version = results[0][0]
    db.close()
    return flask.jsonify(dict(version=version))

@app.route("/q/search")
def Search():
    semester = request.args.get('semester')
    search = request.args.get('search')
    if not semester:
        return flask.jsonify(dict(error="Semester is missing."))
    if not search:
        return flask.jsonify(dict(error="Keywords is missing."))

    answer = schedule.search(dbname, semester, search)
    return flask.jsonify({
        'data': answer
    });
if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=1)
