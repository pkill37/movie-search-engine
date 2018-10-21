from flask import Flask, Response, request, redirect, url_for, render_template, flash
import shlex
from db import PostgresDatabase
import json
import datetime

app = Flask(__name__)
app.secret_key = 'N2gjLwBJNOKfGqIHFxlWhd9nZDn0THsx'
db = PostgresDatabase()


@app.route('/')
def index():
    movies = db.query('SELECT * FROM movies')
    return render_template('index.html', movies=movies)


@app.route('/insert', methods=('GET', 'POST'))
def insert():
    if request.method == 'POST':
        title = request.form['title'].strip()
        categories = request.form['categories'].strip()
        summary = request.form['summary'].strip()
        description = request.form['description'].strip()

        errors = []
        if not title:
            errors += ['Title is required.']
        if not categories:
            errors += ['Categories are required.']
        if not summary:
            errors += ['Summary is required.']
        if not description:
            errors += ['Description is required.']
        if errors:
            for error in errors:
                flash(error)
        else:
            db.query(
                'INSERT INTO movies VALUES(DEFAULT, %s, %s, %s, %s)',
                (title, categories, summary, description)
            )

            return redirect(url_for('index'))
    else:
        return render_template('insert.html')


@app.route('/search', methods=('GET', 'POST'))
def search():
    if request.method == 'POST':
        query = request.form['query'].strip()
        link = request.form['link'].strip()

        errors = []
        if not query:
            errors += ['Query is required.']
        if not link:
            errors += ['Phrases link method is required.']
        if errors:
            for error in errors:
                flash(error)
        else:
            phrases = shlex.split(query)
            phrases = [' & '.join(phrase.split(' ')) for phrase in phrases]

            # Build query
            sql = '''SELECT
    search.id,
    ts_headline(search.title, to_tsquery(%s)) AS title,
    ts_headline(search.categories, to_tsquery(%s)) AS categories,
    ts_headline(search.summary, to_tsquery(%s)) AS summary,
    ts_headline(search.description, to_tsquery(%s)) AS description,
    ts_rank(search.tsv, to_tsquery(%s)) AS rank
FROM (SELECT id, title, categories, summary, description, tsv
      FROM movies
      WHERE tsv @@ to_tsquery(%s)'''
            if link == 'and':
                tsquery = ') & ('.join(phrases)
                for i in range(1, len(phrases)):
                    sql += ' AND tsv @@ to_tsquery(%s)'
            else:
                tsquery = ') | ('.join(phrases)
                for i in range(1, len(phrases)):
                    sql += ' OR tsv @@ to_tsquery(%s)'
            sql += '\n      LIMIT 50) AS search'
            sql += '\nORDER BY rank DESC'
            tsquery = '(' + tsquery + ')'

            args = (tsquery, tsquery, tsquery, tsquery, tsquery, *phrases)
            movies = db.query(sql, args)
            last_executed_query = db.last_executed_query
            db.query('INSERT INTO logs VALUES(DEFAULT, %s, DEFAULT)', (tsquery,))
            return render_template('search.html', movies=movies, query=last_executed_query)
    else:
        return render_template('search.html')


@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    term = request.args.get('term')
    movies = db.query('SELECT title FROM movies WHERE similarity(lower(title), lower(%s)) > 0.1 ORDER BY similarity(lower(title), lower(%s)) DESC LIMIT 5', (term, term))
    titles = [movie.title for movie in movies]
    return Response(json.dumps(titles), mimetype='application/json')


def validate(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY-MM-DD")


def build_date_interval(start, finish):
    dt = datetime.datetime.strptime(start, '%Y-%m-%d')
    end = datetime.datetime.strptime(finish, '%Y-%m-%d')
    step = datetime.timedelta(days=1)

    result = []
    while dt <= end:
        result.append(dt.strftime('%Y-%m-%d'))
        dt += step
    return result


@app.route('/analytics', methods=('GET', 'POST'))
def analytics():
    if request.method == 'POST':
        try:
            start = request.form['start'].strip()
            finish = request.form['finish'].strip()
            granularity = request.form['granularity'].strip()
            validate(start)
            validate(finish)
        except ValueError:
            flash('Invalid start or finish dates')
            return render_template('analytics.html')

        if granularity == 'hour':
            results = db.query('''
            SELECT * FROM crosstab('
                SELECT
                    query,
                    CAST(EXTRACT(HOUR FROM timestamp) AS int) AS hour,
                    CAST(COUNT(*) AS int) AS occurrences
                FROM logs
                WHERE timestamp::date >= '%s' AND timestamp::date <= '%s'
                GROUP BY query, hour
                ORDER BY query, hour
                ', 'SELECT * FROM generate_series(0,23)'
            ) AS pivot (query TEXT, h00_01 INT, h01_02 INT, h02_03 INT, h03_04 INT, h04_05 INT, h05_06 INT, h06_07 INT, h07_08 INT, h08_09 INT, h09_10 INT, h10_11 INT, h11_12 INT, h12_13 INT, h13_14 INT, h14_15 INT, h15_16 INT, h16_17 INT, h17_18 INT, h18_19 INT, h19_20 INT, h20_21 INT, h21_22 INT, h22_23 INT, h23_24 INT)
            ORDER BY query''', (start, finish))
        else:
            sql = '''SELECT * FROM crosstab('
                SELECT
                    query,
                    timestamp::date AS day,
                    CAST(COUNT(*) AS int) AS occurrences
                FROM logs
                WHERE timestamp::date >= '%s' AND timestamp::date <= '%s'
                GROUP BY query, day
                ORDER BY query, day',
                'SELECT d::date FROM generate_series('%s'::date, '%s'::date, ''1 day''::interval) d'
            )'''

            sql += ' AS pivot(query TEXT'
            for d in build_date_interval(start, finish):
                sql += ', d' + d.replace('-', '_') + ' INT'
            sql += ') ORDER BY query'

            results = db.query(sql, (start, finish, start, finish))
        return render_template('analytics.html', results=results)
    else:
        return render_template('analytics.html')


if __name__ == '__main__':
    app.run(debug=True)
