# -*- coding: utf-8 -*-

from sqlite3 import dbapi2 as sqlite3
from flask import Flask, g, render_template, session, request, make_response, url_for, redirect, abort
from jinja2 import Markup
from urlparse import urlparse, urlunparse, urljoin
from functools import partial
import uuid, time, urllib, urllib2, re, sys, os, json

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
    return sqlite3.connect(app.config['DATABASE'], timeout=30)

def generate_user_id():
    return str(uuid.uuid4())

def add_track_record(referrer, destination):
    g.db.execute('INSERT INTO `tracks` (`user_id`, `timestamp`, `referrer`, `destination`) VALUES (?, ?, ?, ?)',
        [ unicode(session.get('user')), int(time.time()), unicode(referrer), unicode(destination) ])
    g.db.commit()

REG_SOURCE = re.compile(r'(href|src)=\s*([\'\"])([^\'\"]+)\2')
CONFIG_FILE_PATH = os.sep.join([app.config.root_path, 'config', ''])

def parse_source_url(m, base_url=None):
    if base_url is None:
        return m.group(0)

    return u'{0}={1}{2}{1}'.format(m.group(1), m.group(2), urljoin(base_url, m.group(3)))

@app.before_request
def before_request():
    g.db = connect_db()
    if not session.get('user'):
        session['user'] = generate_user_id()

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()

@app.route('/')
def index():
    version = request.args.get('ver', None)
    index_links = None

    if version and version.isdigit():
        try:
            links_json = json.load(file('%s%s.json' % (CONFIG_FILE_PATH, version)), 'utf-8')
            if len(links_json) > 0:
                index_links = [ (link['name'], link['url']) for link in links_json ]
        except Exception, e:
            app.logger.error(e)

    return render_template('index.html', index_links=index_links)

REG_CHARSET_SIMPLE = re.compile(r'<meta\s*charset\s*=\s*([\"\'])([^\"\']+)\1\s*>')
REG_CHARSET = re.compile(r'<meta[\s\w=\"\'/;-]+charset=([^\'\"]+)')
REG_DOMAIN = re.compile(r'\.?\w+\.\w+$')

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

    path = urllib.unquote_plus(path)
    parsed_url = urlparse(path)

    # if not REG_DOMAIN.search(parsed_url.netloc) and request.referrer:
    #     base_path = url_for('link', path='__path__').replace('__path__', '')
    #     base_url = urlparse(request.referrer).path.replace(base_path, '')
    #     path = urlunparse((parsed_url.scheme, urlparse(base_url).netloc, '/%s%s' % (parsed_url.netloc, parsed_url.path), '', '', ''))

    if request.method == 'GET' and request.query_string:
        path = '%s?%s' % (path, request.query_string)

    app.logger.debug('try to get content from: %s' % path)

    headers = request.headers

    req = urllib2.Request(path, headers=dict([ ('User-Agent', headers.get('User-Agent')) ]))

    try:
        app.logger.debug('fetching content...')
        site = urllib2.urlopen(req)
    except:
        if request.referrer:
            return redirect(request.referrer)

        abort(404)

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

        decoded = REG_SOURCE.sub(partial(parse_source_url, base_url=path), decoded)
        decoded = decoded.replace('</body>', '<script>var __origin_url__=\'%s\';</script><script src="%s"></script></body>' % (path, url_for('static', filename='js/core.js')))

    return make_response((decoded.encode(charset), 200, { 'Content-Type': 'text/html; charset=%s' % charset })) if charset is not None else make_response(content)

@app.route('/record')
def list_records():
    cur = g.db.execute('SELECT * FROM `tracks`')
    tracks = [ dict(user_id=row[1], time=row[2], ref=row[3], dest=row[4]) for row in cur.fetchall() ]
    return render_template('record.html', tracks=tracks)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
