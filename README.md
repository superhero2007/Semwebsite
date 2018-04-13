# BlurAdmin AngularJS admin panel front-end framework and back-end based on Django Python

Basic REST API based on Django Python

Customizable admin panel framework made by [Akveo team](http://akveo.com/).

## Back-end dependencies (Linux)
- Python 3.6.5
- PIP
- Django 2.0.4
- virtualenv
- virtualenvwrapper

## Front-end dependencies
- NodeJS
- NPM
- Bower
- Gulp

## First steps back-end (Linux)
1. If you don't have a virtualenv created: `mkvirtualenv my_venv`
2. Activate your virtualenv with virtualenvwrapper `workon my_venv`
3. Install back-end dependencies `pip install -r requirements.txt`
4. Run django DB makemigrations `python manage.py makemigrations`
5. Run django DB migrate `python manage.py migrate`
6. Your REST API is running in `localhost:8000`

## For your AngularJS front-end
1. Go to the frontend folder `cd frontend/`
2. Install front-end dependencies `npm install`
3. Run this command `gulp serve`
4. Your frontend is running in `localhost:3000`

## Front-end documentation
Installation, customization and other useful articles: https://akveo.github.io/blur-admin/

## How can I support developers?
- Star our GitHub repo
- Create pull requests, submit bugs, suggest new features or documentation updates

License
-------------
<a href=/LICENSE.txt target="_blank">MIT</a> license.
