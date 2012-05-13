# -*- coding: utf-8 -*-

from sqlite3 import dbapi2 as sqlite3
from flask import Flask, g, render_template, session, request, make_response, url_for, redirect
from jinja2 import Markup
import uuid, time, urllib, urllib2, re, sys

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

@app.template_filter('datetimeformat')
def datetimeformat_filter(value, format='%Y年%m月%d日%H:%M'):
    return time.strftime(format, time.localtime(value)).decode('utf-8')

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
        [ session.get('user'), int(time.time()), referrer, destination ])
    g.db.commit()

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()

@app.route('/')
def index():
    return render_template('index.html')

REG_CHARSET_SIMPLE = re.compile(r'<meta\s*charset\s*=\s*([\"\'])([^\"\']+)\1\s*>')
REG_CHARSET = re.compile(r'<meta[\s\w=\"\'/;-]+charset=([^\'\"]+)')

@app.route('/link/<path:path>')
def link(path):
    if path.find(request.url_root) >= 0:
        return redirect(request.referrer)

    referrer = request.url_root
    if request.referrer:
        reg = re.compile(request.url_root + 'link/(.+)$')
        referrer = urllib.unquote_plus(request.referrer)
        m = reg.match(referrer)
        if m:
            referrer = urllib.unquote_plus(m.group(1))

    headers = request.headers
    if request.method == 'GET' and request.query_string:
        path = '%s?%s' % (path, request.query_string)

    app.logger.debug('try to get content from: %s' % path)

    req = urllib2.Request(path, headers=dict([ ('User-Agent', headers.get('User-Agent')) ]))

    try:
        app.logger.debug('fetching content...')
        site = urllib2.urlopen(req)
    except urllib2.HTTPError:
        return redirect(request.referrer)

    content_type = site.headers.get('content-type')

    app.logger.debug('try to get content...')
    content = site.read()

    charset = None
    if content_type.find('text/html') >= 0:
        app.logger.debug('try to decode source file...')
        add_track_record(referrer, path)

        decoded = None

        # use content charset to dectect like: <meta charset="utf-8">
        m = REG_CHARSET_SIMPLE.search(content)
        if m:
            charset = m.group(2)
            try:
                decoded = content.decode(charset)
            except UnicodeDecodeError:
                decoded = None

        # use content charset to dectect like: <meta http-equiv="Content-Type" ...>
        else:
            m = REG_CHARSET.search(content)
            if m:
                charset = m.group(1)
                try:
                    decoded = content.decode(charset)
                except UnicodeDecodeError:
                    decoded = None

        # use header info to detect
        if decoded is None:
            m = REG_CHARSET.search(content_type)
            if m:
                charset = m.group(1)
                try:
                    decoded = content.decode(charset)
                except UnicodeDecodeError:
                    decoded = None

        # fallback
        if decoded is None:
            charsets = [ 'gbk', 'gb2312', 'utf-8' ]
            charsets.reverse()
            while len(charsets) > 0:
                try:
                    charset = charsets.pop()
                    decoded = content.decode(charset)
                    break
                except UnicodeDecodeError:
                    continue

        app.logger.debug('decoded with %s' % charset)
        #app.logger.debug('encode to utf-8')
        #content = decoded.encode('utf-8')
        #app.logger.debug('insert script tag')
        content = content.replace('</body>', '<script src="%s"></script></body>' % url_for('static', filename='js/core.js'))


    return make_response((content, 200, { 'Content-Type': 'text/html; charset=%s' % charset })) if charset is not None else make_response(content)

@app.route('/record')
def list_records():
    cur = g.db.execute('SELECT * FROM `tracks`')
    tracks = [ dict(user_id=row[1], time=row[2], ref=row[3], dest=row[4]) for row in cur.fetchall() ]
    return render_template('record.html', tracks=tracks)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
