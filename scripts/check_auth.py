"""Run after `npm --prefix frontend run build`; uses a disposable local database.
Starts both servers in one process environment to test actual Next -> Django routing.
"""
import http.cookiejar
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:3100'

def main():
    with tempfile.TemporaryDirectory(prefix='aiman-auth-') as temp:
        env = {**os.environ, 'DJANGO_DEBUG': '1', 'DATABASE_URL': f'sqlite:///{temp}/test.sqlite3',
               'CSRF_TRUSTED_ORIGINS': BASE, 'REDIS_URL': '', 'INTERNAL_API_URL': 'http://127.0.0.1:8000'}
        subprocess.run(['python3', 'manage.py', 'migrate', '--noinput'], cwd=ROOT/'backend', env=env, check=True, stdout=subprocess.DEVNULL)
        processes = []
        with open(f'{temp}/servers.log', 'w+') as log:
            try:
                processes.append(subprocess.Popen(['python3', 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'], cwd=ROOT/'backend', env=env, stdout=log, stderr=log))
                processes.append(subprocess.Popen(['node', 'node_modules/next/dist/bin/next', 'start', '-p', '3100', '-H', '127.0.0.1'], cwd=ROOT/'frontend', env=env, stdout=log, stderr=log))
                cookies = http.cookiejar.CookieJar()
                client = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(cookies))
                def request(path, data=None, token=None, expected=200):
                    headers = {'Origin': BASE, 'Content-Type': 'application/json'}
                    if token: headers['X-CSRFToken'] = token
                    req = urllib.request.Request(BASE+path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
                    try: response = client.open(req, timeout=10)
                    except urllib.error.HTTPError as error: response = error
                    assert response.status == expected, (path, response.status, response.read()[:300])
                    assert response.url == BASE+path, ('Unexpected redirect', path, response.url)
                    return json.loads(response.read())
                for attempt in range(40):
                    try:
                        token=request('/api/csrf/')['csrfToken'];break
                    except (OSError, AssertionError):time.sleep(.25)
                else:raise AssertionError('Servers did not become ready')
                account={'name':'QA Customer','email':'auth-check@example.test','password':'Unique-Celebration-74!','consent':True}
                request('/api/auth/register/', account, expected=403)
                registered=request('/api/auth/register/',account,token,expected=201)['user']
                assert request('/api/auth/me/')['user']['id']==registered['id']
                token=request('/api/csrf/')['csrfToken']
                request('/api/auth/logout/',{},token)
                assert request('/api/auth/me/')['user'] is None
                token=request('/api/csrf/')['csrfToken']
                request('/api/auth/login/',{**account,'password':'wrong-password'},token,expected=400)
                request('/api/auth/login/',account,token)
                assert request('/api/auth/me/')['user']['email']==account['email']
                for path in ['/', '/login', '/register', '/images/home-hero.webp']:
                    with client.open(BASE+path,timeout=20) as response: assert response.status==200
                print('PASS: frontend proxy CSRF, registration, session persistence, logout, invalid/valid login, homepage/auth pages and hero image.')
            except Exception:
                log.flush();log.seek(0);print(log.read()[-6000:]);raise
            finally:
                for process in processes: process.terminate()
                for process in processes:
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:process.kill()

if __name__ == '__main__': main()
