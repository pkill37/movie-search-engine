from flask import Flask, request, redirect, url_for, render_template, flash
import records
import shlex

app = Flask(__name__)
app.secret_key = 'N2gjLwBJNOKfGqIHFxlWhd9nZDn0THsx'
db = records.Database('postgres://fabio@localhost:5432/movie-search-engine')


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
                'INSERT INTO movies (title, categories, summary, description) VALUES(:title, :categories, :summary, :description)',
                title=title, categories=categories, summary=summary, description=description
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
            tsquery = ') & ('.join(phrases) if link == 'and' else ') | ('.join(phrases)
            tsquery = '(' + tsquery + ')'
            print(tsquery)

            results = db.query(
                '''
                SELECT
                    id,
                    title,
                    description
                FROM movies
                WHERE to_tsvector(title) @@ to_tsquery(:tsquery)
                OR to_tsvector(description) @@ to_tsquery(:tsquery)
                ''',
                tsquery=tsquery
            )
            return render_template('search.html', results=results)
    else:
        return render_template('search.html')


@app.route('/analytics')
def analytics():
    return render_template('analytics.html')


if __name__ == "__main__":
    app.run(debug=True)
