from flask import Flask, request, redirect, url_for, render_template, flash
import shlex
from db import PostgresDatabase

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
    id,
    ts_headline(title, to_tsquery(%s)) AS title,
    ts_headline(categories, to_tsquery(%s)) AS categories,
    ts_headline(summary, to_tsquery(%s)) AS summary,
    ts_headline(description, to_tsquery(%s)) AS description,
    ts_rank(tsv, to_tsquery(%s)) AS rank
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
            sql += '\nORDER BY rank DESC'
            tsquery = '(' + tsquery + ')'

            args = (tsquery, tsquery, tsquery, tsquery, tsquery, *phrases)
            movies = db.query(sql, args)
            return render_template('search.html', movies=movies, query=db.last_executed_query)
    else:
        return render_template('search.html')


@app.route('/analytics')
def analytics():
    return render_template('analytics.html')


if __name__ == '__main__':
    app.run(debug=True)
