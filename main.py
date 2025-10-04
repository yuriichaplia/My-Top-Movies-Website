import os
import requests
from dotenv import load_dotenv
from flask_wtf import FlaskForm
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from wtforms.validators import DataRequired
from wtforms import StringField, SubmitField
from sqlalchemy import Integer, String, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from flask import Flask, render_template, redirect, url_for, request

load_dotenv()
app = Flask(__name__)
app.secret_key = 'stringforcsrfsecurityflask'
Bootstrap5(app)

class Base(DeclarativeBase):
    pass
db = SQLAlchemy(model_class=Base)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies-collection.db"
db.init_app(app)

class Movies(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    ranking: Mapped[int] = mapped_column(Integer)
    review: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(String, nullable=False)

class AddMovie(FlaskForm):
    movie_title = StringField(label='Movie Title', validators=[DataRequired()])
    submit = SubmitField(label='Add Movie')

class RateMovieForm(FlaskForm):
    rating = StringField(label='Your rating out of 10 e.g. 7.5', validators=[DataRequired()])
    review = StringField(label='Your review', validators=[DataRequired()])
    submit = SubmitField(label='Done')

def add_movie(title, year, description, rating, ranking, review, img_url) -> None:
    with app.app_context():
        added_movie = Movies(
            title=title,
            year=year,
            description=description,
            rating=rating,
            ranking=ranking,
            review=review,
            img_url=img_url
        )
        db.session.add(added_movie)
        db.session.commit()

@app.route("/")
def home():
    movies = db.session.execute(db.select(Movies).order_by(Movies.rating)).scalars().all()
    for index in range(0, len(movies)):
        movies[index].ranking = len(movies) - index
    return render_template("index.html", movies=movies)

@app.route("/edit", methods=["GET", "POST"])
def edit():
    movie_id = request.args.get("id")
    form = RateMovieForm()
    if form.validate_on_submit():
        movie_selected = db.session.execute(db.select(Movies).filter_by(id=movie_id)).scalar_one()
        movie_selected.rating = float(form.rating.data)
        movie_selected.review = form.review.data
        db.session.commit()
        return redirect(url_for('home'))

    movie_selected = db.get_or_404(Movies, movie_id)
    return render_template("edit.html", movie=movie_selected, form=form)

@app.route("/delete")
def delete():
    movie_id = request.args.get("id")
    movie_selected = db.session.execute(db.select(Movies).filter_by(id=movie_id)).scalar_one()
    db.session.delete(movie_selected)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/add', methods=["GET", "POST"])
def add():
    form = AddMovie()
    if form.validate_on_submit():
        url = 'https://api.themoviedb.org/3/search/movie'
        parameters = {
            'query': form.movie_title.data,
        }
        header = {
            'Authorization': f"Bearer {os.environ.get('ACCESS_TOKEN')}"
        }
        response = requests.get(url, params=parameters, headers=header)
        response.raise_for_status()
        response = response.json()['results']
        return render_template('select.html', data=response)
    return render_template('add.html', form=form)

@app.route('/add_from_list', methods=["GET", "POST"])
def add_from_list():
    movie_id = int(request.args.get('id'))

    url = f'https://api.themoviedb.org/3/movie/{movie_id}'
    header = {
        'Authorization': f"Bearer {os.environ.get('ACCESS_TOKEN')}"
    }
    response = requests.get(url, headers=header)
    response.raise_for_status()
    response = response.json()

    title = response['title']
    year = int(response['release_date'].split('-')[0])
    img_url = f"https://image.tmdb.org/t/p/original{response['poster_path']}"
    description = response['overview']
    add_movie(title, year, description, 0.0,  '', '', img_url)

    movie = db.session.execute(db.select(Movies).where(Movies.title==title)).scalar_one()
    return redirect(url_for('edit', id=movie.id))

if __name__ == '__main__':
    app.run(debug=True)