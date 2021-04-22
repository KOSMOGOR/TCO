from flask import Flask, render_template, redirect, make_response, session, request, jsonify, send_from_directory
from flask.blueprints import Blueprint
from werkzeug.exceptions import abort
from data import db_session, news_api
from data.login_form import LoginForm
from data.users import User
from data.news import News
from data.yt_src import Yt
from forms.news import NewsForm
from forms.user import RegisterForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import requests
import xmltodict
import datetime

import json
with open('db/roles.json', encoding='UTF-8') as f:
    dsroles = json.load(f)['roles']
lastcheck = datetime.datetime.now()

app = Flask(__name__, subdomain_matching=True)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['SERVER_NAME'] = 'kosmogor.xyz:5000'
tco = Blueprint('tco', __name__, subdomain='tco')
login_manager = LoginManager()
login_manager.init_app(app)


def check_new_videos():
    db_sess = db_session.create_session()
    res = requests.get('https://www.youtube.com/feeds/videos.xml?channel_id=UC_yvFLQQcIrrQa3eSF7VsEw').text
    rssvideos = [dict(x)['id'].split(':')[-1] for x in dict(xmltodict.parse(res))['feed']['entry']]
    videos = [x.yt_id for x in db_sess.query(Yt)]
    for link in rssvideos[::-1]:
        if link not in videos:
            video = Yt(yt_id=link)
            db_sess.add(video)
            db_sess.commit()
    for link in videos:
        if link not in rssvideos:
            db_sess.query(Yt).filter(Yt.yt_id == link).delete()
            db_sess.commit()


def main():
    db_session.global_init("db/blogs.db")
    check_new_videos()
    app.register_blueprint(tco)
    app.register_blueprint(news_api.blueprint)
    app.run(host='0.0.0.0', port='5000')


@tco.route('/static/<path:path>')
def send_js(path):
    return send_from_directory('static', path)


@tco.route("/")
def index():
    db_sess = db_session.create_session()
    news = db_sess.query(News).filter(News.is_private != True)
    if current_user.is_authenticated:
        news = db_sess.query(News).filter(
            (News.user == current_user) | (News.is_private != True))
    else:
        news = db_sess.query(News).filter(News.is_private != True)
    return render_template("index.html", news=news)


@tco.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@tco.route("/session_test")
def session_test():
    visits_count = session.get('visits_count', 0)
    session['visits_count'] = visits_count + 1
    return make_response(
        f"Вы пришли на эту страницу {visits_count + 1} раз")


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@tco.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@tco.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@tco.route('/news',  methods=['GET', 'POST'])
@login_required
def add_news():
    form = NewsForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        news = News()
        news.title = form.title.data
        news.content = form.content.data
        news.is_private = form.is_private.data
        current_user.news.append(news)
        db_sess.merge(current_user)
        db_sess.commit()
        return redirect('/')
    return render_template('news.html', title='Добавление новости',
                           form=form)


@tco.route('/news/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_news(id):
    form = NewsForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id,
                                          News.user == current_user
                                          ).first()
        if news:
            form.title.data = news.title
            form.content.data = news.content
            form.is_private.data = news.is_private
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id,
                                          News.user == current_user
                                          ).first()
        if news:
            news.title = form.title.data
            news.content = form.content.data
            news.is_private = form.is_private.data
            db_sess.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('news.html',
                           title='Редактирование новости',
                           form=form
                           )


@tco.route('/news_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def news_delete(id):
    db_sess = db_session.create_session()
    news = db_sess.query(News).filter(News.id == id,
                                      News.user == current_user
                                      ).first()
    if news:
        db_sess.delete(news)
        db_sess.commit()
    else:
        abort(404)
    return redirect('/')


@tco.route('/dsroles')
@login_required
def roles():
    return render_template('roles_and_instructions.html', roles=dsroles)


@tco.route('/tcodergad')
@login_required
def degrad():
    global lastcheck
    if (datetime.datetime.now() - lastcheck).seconds >= 60:
        check_new_videos()
        lastcheck = datetime.datetime.now()
    db_sess = db_session.create_session()
    videos = [f'https://www.youtube.com/embed/{x.yt_id}' for x in db_sess.query(Yt)[::-1]]
    return render_template('degrad.html', videos=videos)


@tco.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@tco.errorhandler(401)
def not_authorized(error):
    return render_template('not_authorized.html')


@tco.route('/api/news')
def get_news():
    db_sess = db_session.create_session()
    news = db_sess.query(News).all()
    return jsonify(
        {
            'news':
                [item.to_dict(only=('title', 'content', 'user.name'))
                 for item in news]
        }
    )


@tco.route('/api/news/<int:news_id>', methods=['GET'])
def get_one_news(news_id):
    db_sess = db_session.create_session()
    news = db_sess.query(News).get(news_id)
    if not news:
        return jsonify({'error': 'Not found'})
    return jsonify(
        {
            'news': news.to_dict(only=(
                'title', 'content', 'user_id', 'is_private'))
        }
    )


if __name__ == '__main__':
    main()