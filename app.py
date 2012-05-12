# -*- coding: utf-8 -*-

from sqlite3 import dbapi2 as sqlite3
from flask import Flask, g, render_template, session, request, make_response, url_for, redirect
from jinja2 import Markup
from time import time
import uuid, urllib, urllib2, re

# configuration
DATABASE = 'historytrack.db'
DEBUG = True
SECRET_KEY = '5Y\r\xb3\xb0\x07N\xedj\xaa\n\x9c\xde\xe1\xd8\xc7!\xfa<\xdb\xcf\xc4\xf5\xc3'
#USERNAME = 'admin'
#PASSWORD = '123456'

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

@app.template_filter('urlencode')
def urlencode_filter(s):
    if type(s) == 'Markup':
        s = s.unescape()
    s = s.encode('utf8')
    s = urllib.quote_plus(s)
    return Markup(s)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

@app.before_request
def before_request():
    g.db = connect_db()
    if not session.get('user'):
        session['user'] = generate_user_id()

def generate_user_id():
    return str(uuid.uuid4())

def add_track_record(referrer, destination):
    g.db.execute('INSERT INTO `tracks` (`user_id`, `timestamp`, `referrer`, `destination`) VALUES (?, ?, ?, ?)',
        [ session.get('user'), int(time()), referrer, destination ])
    g.db.commit()

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/link/<path:path>/')
def link(path):
    if path.find(request.url_root) >= 0:
        return redirect(request.referrer)

    referrer = url_for('index')
    if request.referrer:
        reg = re.compile(request.url_root + 'link/(.+)$')
        referrer = urllib.unquote_plus(request.referrer)
        m = reg.match(referrer)
        if m:
            referrer = urllib.unquote_plus(m.group(1))

    headers = request.headers
    req = urllib2.Request(path, headers=dict([ ('User-Agent', headers.get('User-Agent')) ]))

    try:
        app.logger.debug('fetching content...')
        site = urllib2.urlopen(req)
        app.logger.debug('fetching done')
    except urllib2.HTTPError:
        return redirect(request.referrer)

    content_type = site.headers.get('content-type')

    app.logger.debug('try to get content...')
    content = site.read()
    app.logger.debug('get content done')
    if content_type.find('text/html') >= 0:
        app.logger.debug('try to decode source file...')
        add_track_record(referrer, path)
        m = re.search('charset=([\w-]+)$', content_type)
        if m:
            charset = m.group(1)
            decoded = content.decode(charset)
        else:
            charsets = [ 'gbk', 'utf-8' ]
            charsets.reverse()
            while len(charsets) > 0:
                try:
                    decoded = content.decode(charsets.pop())
                    break
                except UnicodeDecodeError:
                    continue

        app.logger.debug('encode to utf-8')
        content = decoded.encode('utf-8')
        app.logger.debug('insert script tag')
        content = content.replace('</body>', '<script src="%s"></script></body>' % url_for('static', filename='js/core.js'))

    return make_response(content)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
