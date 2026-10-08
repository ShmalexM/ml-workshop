"""The optional AI assistant: stream parsers, URL policy, key storage, proxying, cancellation and limits.

Integration tests run a disposable workshop server against tests/fake_llm.py. No real provider is called.
"""
import http.client
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import assistant  # noqa: E402
import assistant_providers as providers  # noqa: E402
from fake_llm import ANSWER, NDJSON_PIECES, SSE_PIECES, FakeLLM  # noqa: E402
from server_fixture import server_token  # noqa: E402

KEY = 'sk-test-0123456789abcdefWXYZ'
POSIX = os.name != 'nt'


def split_everywhere(data):
    """Every way to cut the bytes in two, plus one byte at a time."""
    yield [data]
    for cut in range(1, len(data)):
        yield [data[:cut], data[cut:]]
    yield [data[i:i + 1] for i in range(len(data))]


def decode(protocol, pieces):
    decoder = providers.StreamDecoder(protocol)
    events = [event for piece in pieces for event in decoder.feed(piece)]
    return events + decoder.close()


class ParserTests(unittest.TestCase):
    def check(self, protocol, data):
        for pieces in split_everywhere(data):
            events = decode(protocol, pieces)
            self.assertEqual(''.join(v for k, v in events if k == 'delta'), ANSWER)
            self.assertEqual(events[-1], ('done', None))

    def test_openai_stream_in_any_split(self):
        self.check('openai', b''.join(SSE_PIECES))

    def test_ollama_stream_in_any_split(self):
        self.check('ollama', b''.join(NDJSON_PIECES))

    def test_sse_fields(self):
        parser = providers.SSEParser()
        events = parser.feed(b': comment\r\nevent: x\r\nid: 4\r\ndata: one\r\ndata:two\r\n\r\nretry: 5\rdata: three\r\r\n')
        self.assertEqual(events, ['one\ntwo', 'three'])
        # A lone CR at the end can be half of CRLF, so the line waits for the next byte.
        parser = providers.SSEParser()
        self.assertEqual(parser.feed(b'data: a\r'), [])
        self.assertEqual(parser.feed(b'\n\r\n'), ['a'])

    def test_errors_in_streams(self):
        self.assertEqual(decode('openai', [b'data: {"error":{"message":"No credit"}}\n\n']), [('error', 'No credit')])
        self.assertEqual(decode('ollama', [b'{"error":"model \\"x\\" not found"}\n']), [('error', 'model "x" not found')])
        # Lines that are not JSON are skipped.
        self.assertEqual(decode('openai', [b'data: {oops\n\ndata: [DONE]\n\n']), [('done', None)])

    def test_reasoning_is_reported_but_not_shown(self):
        self.assertEqual(decode('openai', [b'data: {"choices":[{"delta":{"reasoning":"Let me see"}}]}\n\n']), [('thinking', None)])
        self.assertEqual(decode('ollama', [b'{"message":{"content":"","thinking":"Hmm"},"done":false}\n']), [('thinking', None)])

    def test_redact(self):
        text = f'key {KEY} and Bearer abc.def-123 and sk-otherkey12345678'
        self.assertNotIn(KEY, providers.redact(text, KEY))
        self.assertNotIn('abc.def', providers.redact(text))
        self.assertNotIn('otherkey', providers.redact(text))

    def test_request_bodies(self):
        path, body = providers.chat_request('ollama', 'ollama', 'm', [], 800)
        self.assertEqual(path, '/api/chat')
        self.assertEqual(json.loads(body)['options']['num_ctx'], providers.OLLAMA_CONTEXT)
        self.assertIs(json.loads(body)['think'], False)
        _, body = providers.chat_request('openai', 'openai', 'm', [], 800)
        self.assertEqual(json.loads(body)['max_completion_tokens'], 800)
        _, body = providers.chat_request('openai', 'openrouter', 'm', [], 800)
        self.assertEqual(json.loads(body)['max_tokens'], 800)


def resolver(table):
    def resolve(host, port):
        if host in table:
            return table[host]
        raise assistant.PolicyError('Cannot find ' + host)
    return resolve


class URLPolicyTests(unittest.TestCase):
    OWN = 7432
    DNS = staticmethod(resolver({
        'openrouter.ai': ['104.18.2.115'],
        'localhost': ['::1', '127.0.0.1'],
        '127.0.0.1': ['127.0.0.1'],
        '::1': ['::1'],
        'metadata.test': ['169.254.169.254'],
        'rebind.test': ['93.184.216.34', '169.254.169.254'],
        'v6meta.test': ['fd00:ec2::254'],
        'private.test': ['10.1.2.3'],
    }))

    def test_allowed(self):
        for url in ['https://openrouter.ai/api/v1', 'http://127.0.0.1:11434', 'http://localhost:1234/v1',
                    'http://[::1]:11434', 'https://private.test/v1', 'HTTP://127.0.0.1:8080/v1/']:
            with self.subTest(url=url):
                target = assistant.check_base_url(url, self.OWN, self.DNS)
                self.assertTrue(target.addresses)

    def test_rejected(self):
        for url in ['ftp://openrouter.ai/', 'file:///etc/passwd', 'javascript:alert(1)', 'gopher://127.0.0.1:70/',
                    'ws://127.0.0.1:11434', '//openrouter.ai/api', 'openrouter.ai/api/v1', '',
                    'http://example.com/v1', 'http://192.168.1.10:11434', 'http://private.test/v1',
                    'http://localhost.evil.test:11434',
                    'https://169.254.169.254/latest/meta-data', 'https://[fe80::1]/', 'https://[::ffff:169.254.169.254]/',
                    'https://0.0.0.0/', 'https://0.1.2.3/', 'https://224.0.0.1/', 'https://100.100.100.200/',
                    'https://metadata.test/', 'https://rebind.test/', 'https://v6meta.test/',
                    'https://user:pass@openrouter.ai/api/v1', 'https://openrouter.ai/api/v1?x=1', 'https://openrouter.ai/#a',
                    f'http://127.0.0.1:{self.OWN}', f'http://localhost:{self.OWN}/v1', 'http://127.0.0.1:7318',
                    'https://openrouter.ai:99999/', 'http://127.0.0.1:11434/v\n1', 'http://127.0.0.1:11434/a b']:
            with self.subTest(url=url), self.assertRaises(assistant.PolicyError):
                assistant.check_base_url(url, self.OWN, self.DNS)


class Workshop:
    """A disposable server. Its stderr goes to server.log in the data folder, as with the launcher."""

    def __init__(self, data, **env):
        self.data = Path(data)
        self.data.mkdir(exist_ok=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        assert self.port != 7318, 'Refusing the production port'
        self.url = f'http://127.0.0.1:{self.port}'
        self.log = (self.data / 'server.log').open('ab')
        self.proc = subprocess.Popen([sys.executable, str(ROOT / 'backend/server.py'), '--port', str(self.port)],
                                     env={**os.environ, 'ML_WORKSHOP_DATA_DIR': str(self.data), **env},
                                     stdout=self.log, stderr=self.log)
        self.token = server_token(self.url, self.data, self.proc)

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.log.close()

    def request(self, path, body=None, token=None, headers=None):
        """Return (status, body bytes). token='' sends no token."""
        token = self.token if token is None else token
        head = {'Content-Type': 'application/json'} if body is not None else {}
        if token:
            head['X-Workshop-Token'] = token
        head.update(headers or {})
        request = urllib.request.Request(self.url + path, data=None if body is None else json.dumps(body).encode(), headers=head)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            with error:
                return error.code, error.read()

    def json(self, path, body=None, **kw):
        status, raw = self.request(path, body, **kw)
        return status, json.loads(raw)

    def open_chat(self, body):
        """Start a chat and return (connection, response) for reading lines. connection.socket stays set."""
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=30)
        connection.request('POST', '/api/assistant/chat', body=json.dumps(body),
                           headers={'Content-Type': 'application/json', 'X-Workshop-Token': self.token})
        # getresponse() hands the socket to the response and clears connection.sock.
        connection.socket = connection.sock
        return connection, connection.getresponse()

    def chat(self, body):
        """Run a chat to the end. Returns (status, events or error object)."""
        connection, response = self.open_chat(body)
        try:
            raw = response.read()
            if response.status != 200:
                return response.status, json.loads(raw)
            return 200, [json.loads(line) for line in raw.splitlines() if line.strip()]
        finally:
            connection.close()


def question(text='Why does my loop stop early?', **extra):
    body = dict(pageKind='lesson', page='Learn', mode='chat', messages=[{'role': 'user', 'content': text}],
                context=[{'id': 'lesson', 'label': 'Lesson', 'text': 'Python from zero 4: for loops. Stage: Try it yourself.'},
                         {'id': 'code', 'label': 'Your code', 'text': 'for i in range(3):\n    print(i)\n'}])
    body.update(extra)
    return body


def wait_idle(server):
    """Wait until the server has finished with the last stream, such as one whose browser just went away."""
    for _ in range(100):
        if not server.json('/api/assistant/config')[1]['busy']:
            return
        time.sleep(0.02)
    raise AssertionError('The stream lock stayed held')


def deltas(events):
    return ''.join(e['text'] for e in events if e['type'] == 'delta')


class AssistantServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = FakeLLM()
        cls.other = FakeLLM()
        cls.tmp = tempfile.TemporaryDirectory(prefix='ml-assistant-test-')
        cls.server = Workshop(Path(cls.tmp.name) / 'data')

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.fake.stop()
        cls.other.stop()
        cls.tmp.cleanup()

    def setUp(self):
        # A test that failed mid-stream must not leave its answer running for the next one.
        self.server.json('/api/assistant/stop', {})
        wait_idle(self.server)
        self.fake.reset()
        self.other.reset()

    def configure(self, **settings):
        body = dict(enabled=True, provider='custom', baseUrl=self.fake.url + '/v1', model='fake-model', allowSolutions=False)
        body.update(settings)
        status, config = self.server.json('/api/assistant/config', body)
        self.assertEqual(status, 200, config)
        return config

    def wait_until_idle(self):
        wait_idle(self.server)

    def test_00_off_by_default_and_silent(self):
        status, config = self.server.json('/api/assistant/config')
        self.assertEqual(status, 200)
        self.assertFalse(config['enabled'])
        self.assertFalse(config['ready'])
        self.assertFalse(config['hasKey'])
        self.assertFalse((self.server.data / 'assistant.json').exists())
        for path in ('/api/assistant/chat', '/api/assistant/test', '/api/assistant/models'):
            status, reply = self.server.json(path, question())
            self.assertEqual(status, 409, reply)
        self.assertEqual(self.fake.requests, [])

    def test_token_and_origin_required(self):
        self.configure()
        for path, body in [('/api/assistant/config', None), ('/api/assistant/config', {'enabled': False}),
                           ('/api/assistant/chat', question()), ('/api/assistant/models', {}),
                           ('/api/assistant/test', {}), ('/api/assistant/stop', {})]:
            with self.subTest(path=path, method='GET' if body is None else 'POST'):
                status, reply = self.server.json(path, body, token='')
                self.assertEqual(status, 403)
                self.assertEqual(reply.get('code'), 'session-expired')
                status, _ = self.server.json(path, body, token='x' * 43)
                self.assertEqual(status, 403)
                status, _ = self.server.json(path, body, headers={'Origin': 'https://evil.example'})
                self.assertEqual(status, 403)
        self.assertEqual(self.fake.requests, [])
        status, config = self.server.json('/api/assistant/config')
        self.assertTrue(config['enabled'])

    def test_url_policy_on_save(self):
        self.configure()
        for url in ['ftp://example.com/v1', 'http://example.com/v1', 'https://169.254.169.254/', f'http://127.0.0.1:{self.server.port}',
                    'http://user:pw@127.0.0.1:11434', 'javascript:alert(1)']:
            with self.subTest(url=url):
                status, reply = self.server.json('/api/assistant/config', dict(enabled=True, provider='custom', baseUrl=url, model='m'))
                self.assertEqual(status, 400, reply)
                self.assertIn('error', reply)
        status, config = self.server.json('/api/assistant/config')
        self.assertEqual(config['baseUrl'], self.fake.url + '/v1')

    def test_key_is_never_returned_or_exported(self):
        config = self.configure(key=KEY)
        self.assertTrue(config['hasKey'])
        self.assertEqual(config['keyLast4'], 'WXYZ')
        self.assertNotIn(KEY, json.dumps(config))
        file = self.server.data / 'assistant.json'
        if POSIX:
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)
        self.assertIn(KEY, file.read_text())
        status, events = self.server.chat(question())
        self.assertEqual(status, 200, events)
        self.assertEqual(self.fake.requests[-1]['headers'].get('Authorization'), 'Bearer ' + KEY)
        self.wait_until_idle()
        for path in ['/api/assistant/config', '/api/state', '/api/runtime', '/api/portfolio', '/api/library', '/api/curriculum',
                     '/api/game', '/api/game/summary', '/api/health', '/api/session', '/']:
            with self.subTest(path=path):
                status, raw = self.server.request(path)
                # / answers 503 when the front end is not built.
                self.assertIn(status, (200, 503) if path == '/' else (200,))
                self.assertNotIn(KEY.encode(), raw)
                self.assertNotIn(b'0123456789abcdef', raw)
        for path in ['/api/assistant/models', '/api/assistant/test']:
            status, raw = self.server.request(path, {})
            self.assertEqual(status, 200, raw)
            self.assertNotIn(KEY.encode(), raw)
        status, backup = self.server.json('/api/backup', {})
        self.assertEqual(status, 200)
        status, raw = self.server.request(backup['url'])
        self.assertEqual(status, 200)
        self.assertNotIn(KEY.encode(), raw)
        self.assertNotIn(KEY, (self.server.data / 'backups' / backup['filename']).read_text())
        # Saving without a key keeps it; Remove key deletes it.
        self.assertTrue(self.configure(model='fake-model-2')['hasKey'])
        config = self.configure(removeKey=True)
        self.assertFalse(config['hasKey'])
        self.assertNotIn(KEY, file.read_text())

    def test_key_only_goes_to_the_address_it_was_saved_for(self):
        self.configure(key=KEY)
        config = self.configure(baseUrl=self.other.url + '/v1')
        self.assertTrue(config['keyRemoved'])
        self.assertFalse(config['hasKey'])
        self.server.chat(question())
        self.assertNotIn('Authorization', self.other.requests[-1]['headers'])
        self.wait_until_idle()

    def test_openai_compatible_stream(self):
        self.configure(key=KEY)
        status, events = self.server.chat(question())
        self.assertEqual(status, 200, events)
        self.assertEqual(events[0]['type'], 'meta')
        self.assertEqual(events[0]['model'], 'fake-model')
        self.assertEqual(deltas(events), ANSWER)
        self.assertEqual(events[-1]['type'], 'done')
        sent = self.fake.requests[-1]
        self.assertEqual(sent['path'], '/v1/chat/completions')
        body = sent['body']
        self.assertTrue(body['stream'])
        self.assertEqual(body['max_tokens'], assistant.MAX_TOKENS)
        system, user = body['messages'][0], body['messages'][-1]
        self.assertEqual(system['role'], 'system')
        self.assertIn('Do not write the exercise solution', system['content'])
        self.assertIn('Show solution', system['content'])
        tag = system['content'].split('<', 1)[1].split('>', 1)[0]
        self.assertTrue(tag.startswith('workshop-context-'))
        self.assertTrue(user['content'].startswith(f'<{tag}>'))
        self.assertIn('for i in range(3)', user['content'])
        self.assertTrue(user['content'].endswith('Why does my loop stop early?'))
        self.wait_until_idle()

    def test_full_solutions_setting_changes_the_prompt(self):
        self.configure(allowSolutions=True)
        self.server.chat(question(mode='explain'))
        system = self.fake.requests[-1]['body']['messages'][0]['content']
        self.assertIn('give the full solution', system)
        self.assertIn('how to fix it', system)
        self.assertNotIn('Do not write the exercise solution', system)
        self.wait_until_idle()
        self.configure(allowSolutions=False)
        self.server.chat(question(mode='explain'))
        self.assertIn('Do not rewrite the code', self.fake.requests[-1]['body']['messages'][0]['content'])
        self.wait_until_idle()

    def test_ollama_stream(self):
        self.configure(provider='ollama', baseUrl=self.fake.url, model='llama3.2:1b', key=KEY)
        status, events = self.server.chat(question())
        self.assertEqual(status, 200, events)
        self.assertEqual(deltas(events), ANSWER)
        sent = self.fake.requests[-1]
        self.assertEqual(sent['path'], '/api/chat')
        self.assertEqual(sent['body']['options']['num_ctx'], providers.OLLAMA_CONTEXT)
        self.assertNotIn('Authorization', sent['headers'])
        status, reply = self.server.json('/api/assistant/models', {})
        self.assertEqual(reply['models'], ['llama3.2:1b', 'qwen2.5-coder:7b'])
        self.wait_until_idle()

    def test_models_and_test_connection(self):
        self.configure()
        status, reply = self.server.json('/api/assistant/models', {})
        self.assertEqual((status, reply['models']), (200, ['fake-model', 'fake-model-2']))
        status, reply = self.server.json('/api/assistant/test', {})
        self.assertEqual(status, 200, reply)
        self.assertTrue(reply['ok'])
        self.assertEqual(reply['reply'], ANSWER)

    def test_midstream_error(self):
        self.configure()
        self.fake.mode = 'midstream'
        status, events = self.server.chat(question())
        self.assertEqual(status, 200)
        self.assertEqual(deltas(events), 'Hel')
        self.assertEqual(events[-1]['type'], 'error')
        self.assertIn('model crashed', events[-1]['message'])
        self.wait_until_idle()

    def test_closing_the_browser_cancels_upstream(self):
        self.configure()
        self.fake.mode = 'endless'
        connection, response = self.server.open_chat(question())
        self.assertEqual(response.status, 200)
        while json.loads(response.readline())['type'] != 'delta':
            pass
        closed = time.monotonic()
        connection.socket.shutdown(socket.SHUT_RDWR)
        response.close()
        connection.close()
        for _ in range(100):
            if self.fake.closed:
                break
            time.sleep(0.02)
        self.assertTrue(self.fake.closed, 'The provider connection stayed open')
        self.assertLess(self.fake.closed[0] - closed, 1.0)
        self.wait_until_idle()

    def test_stop_ends_the_stream_and_upstream(self):
        self.configure()
        self.fake.mode = 'endless'
        connection, response = self.server.open_chat(question())
        first = json.loads(response.readline())
        self.assertEqual(first['type'], 'meta')
        lines = queue.Queue()
        reader = threading.Thread(target=lambda: [lines.put(json.loads(line)) for line in response], daemon=True)
        reader.start()
        # One stream at a time.
        status, reply = self.server.json('/api/assistant/chat', question())
        self.assertEqual(status, 409, reply)
        # Other requests are not blocked while an answer streams.
        started = time.monotonic()
        self.assertEqual(self.server.json('/api/state')[0], 200)
        self.assertEqual(self.server.json('/api/draft', {'lessonId': 'foundations-1', 'code': 'x = 1', 'notes': '', 'updatedAt': 1})[0], 200)
        self.assertLess(time.monotonic() - started, 2)
        # A Stop for another answer does nothing.
        status, reply = self.server.json('/api/assistant/stop', {'id': 'not-this-one'})
        self.assertEqual((status, reply['stopped']), (200, False))
        stopped = time.monotonic()
        status, reply = self.server.json('/api/assistant/stop', {'id': first['id']})
        self.assertEqual((status, reply['stopped']), (200, True))
        reader.join(5)
        connection.close()
        events = []
        while not lines.empty():
            events.append(lines.get())
        self.assertEqual(events[-1], {'type': 'done', 'stopped': True})
        for _ in range(100):
            if self.fake.closed:
                break
            time.sleep(0.02)
        self.assertTrue(self.fake.closed)
        self.assertLess(self.fake.closed[0] - stopped, 1.0)
        self.wait_until_idle()

    def test_redirects_are_not_followed(self):
        self.configure()
        self.fake.mode = 'redirect'
        self.fake.redirect_to = self.other.url + '/v1/chat/completions'
        status, events = self.server.chat(question())
        self.assertEqual(status, 200)
        self.assertEqual(events[-1]['type'], 'error')
        self.assertIn('redirect', events[-1]['message'])
        status, reply = self.server.json('/api/assistant/models', {})
        self.assertEqual(status, 502)
        self.assertIn('redirect', reply['error'])
        self.assertEqual(self.other.requests, [])
        self.wait_until_idle()

    def test_provider_errors_never_echo_the_key(self):
        self.configure(key=KEY)
        self.fake.mode = 'status'
        for status_code, words in [(401, 'refused the API key'), (429, 'rate-limited'), (404, 'did not find'), (500, 'had an error')]:
            with self.subTest(status=status_code):
                self.fake.status = status_code
                status, events = self.server.chat(question())
                self.assertEqual(status, 200)
                self.assertIn(words, events[-1]['message'])
                self.assertIn('[redacted]', events[-1]['message'])
                self.assertNotIn(KEY, json.dumps(events))
                self.wait_until_idle()
                for path in ('/api/assistant/models', '/api/assistant/test'):
                    status, raw = self.server.request(path, {})
                    self.assertEqual(status, 502)
                    self.assertNotIn(KEY.encode(), raw)
        self.assertEqual(self.fake.requests[0]['headers']['Authorization'], 'Bearer ' + KEY)

    def test_bad_chat_requests(self):
        self.configure()
        for body in [dict(question(), pageKind='battle'), dict(question(), mode='solve'), dict(question(), messages=[]),
                     dict(question(), messages=[{'role': 'system', 'content': 'x'}]),
                     dict(question(), messages=[{'role': 'user', 'content': 'x' * 20000}]),
                     dict(question(), context=[{'id': 'solution', 'label': 'S', 'text': 'x'}]),
                     dict(question(), context=[{'id': 'code', 'label': 'Code', 'text': 'x' * 13000}])]:
            status, reply = self.server.json('/api/assistant/chat', body)
            self.assertEqual(status, 400, reply)
        self.assertEqual(self.fake.requests, [])

    def test_zz_server_log_has_no_key(self):
        self.configure(key=KEY)
        self.fake.mode = 'status'
        self.server.chat(question())
        self.wait_until_idle()
        self.server.request('/api/assistant/models', {})
        log = (self.server.data / 'server.log').read_bytes()
        self.assertIn(b'/api/assistant/chat', log)
        self.assertNotIn(KEY.encode(), log)
        self.assertNotIn(b'0123456789abcdef', log)


class RateLimitTests(unittest.TestCase):
    def test_rate_limit(self):
        fake = FakeLLM()
        with tempfile.TemporaryDirectory(prefix='ml-assistant-limit-') as tmp:
            server = Workshop(Path(tmp) / 'data', ML_WORKSHOP_ASSISTANT_LIMIT='2')
            try:
                status, _ = server.json('/api/assistant/config', dict(enabled=True, provider='custom', baseUrl=fake.url + '/v1', model='fake-model'))
                self.assertEqual(status, 200)
                for _ in range(2):
                    status, events = server.chat(question())
                    self.assertEqual(status, 200, events)
                    wait_idle(server)
                status, reply = server.json('/api/assistant/chat', question())
                self.assertEqual(status, 429, reply)
                self.assertIn('Too many messages', reply['error'])
                status, reply = server.json('/api/assistant/test', {})
                self.assertEqual(status, 429)
                self.assertEqual(len([r for r in fake.requests if r['method'] == 'POST']), 2)
            finally:
                server.stop()
                fake.stop()

    def test_window(self):
        limit = assistant.RateLimit(2, window=0.2)
        self.assertTrue(limit.take())
        self.assertTrue(limit.take())
        self.assertFalse(limit.take())
        time.sleep(0.25)
        self.assertTrue(limit.take())


if __name__ == '__main__':
    unittest.main()
