from flask import Flask, request, redirect, url_for, render_template, flash
import records

app = Flask(__name__)
app.secret_key = 'N2gjLwBJNOKfGqIHFxlWhd9nZDn0THsx'
db = records.Database('postgres://fabio@localhost:5432/movie-search-engine')


@app.route('/')
def index():
    movies = db.query('SELECT * FROM movies')
    return render_template('index.html', movies=movies)


@app.route('/insert', methods=('GET', 'POST'))
def insert(name=None):
    if request.method == 'POST':
        title = request.form['title']
        categories = request.form['categories']
        summary = request.form['summary']
        description = request.form['description']

        errors = []
        if not title.strip():
            errors += ['Title is required.']
        if not categories.strip():
            errors += ['Categories are required.']
        if not summary.strip():
            errors += ['Summary is required.']
        if not description.strip():
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

    return render_template('insert.html')


@app.route('/search')
def search():
    return render_template('search.html')


@app.route('/analytics')
def analytics():
    return render_template('analytics.html')


if __name__ == "__main__":
    app.run()
