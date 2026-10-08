"""A fake AI provider for the assistant tests: Ollama and OpenAI-compatible routes on 127.0.0.1:0.

Set `mode` to choose the behaviour of the next chat request: ok, status, redirect, slow, endless or
midstream. Answers that are not from an AI provider: empty and html answer 200 with an empty body or an HTML
page on every route. plain sends one JSON chat answer without streaming, and early sends part of a stream
with no end marker. Hostile modes: echo and echostream send the key back changed; flood, nonl and noise send a
stream that never ends a line, never ends an event, or never ends; slowhead and slowerror send headers or an
error body one byte at a time, and slowbody does the same for a model list. Every request is recorded in
`requests`; `closed` gets the time.monotonic() at which an endless or slow answer saw its client go away.
"""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import select
import socket
import threading
import time

# Byte strings split on purpose: a CRLF event, a comment, a line split across writes and a split UTF-8 character.
SSE_PIECES = [
    b': keep-alive\r\n\r\n',
    b'data: {"choices":[{"delta":{"role":"assistant"}}]}\r\n\r\n',
    b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n',
    b'\ndata: {"choices":[{"delta":{"content":"lo \xc3',
    b'\xa9 \xe2\x9c',
    b'\x93"}}]}\n\n',
    b'data: [DONE]\n\n',
]
NDJSON_PIECES = [
    b'{"message":{"role":"assistant","content":"Hel"},"done":false}\n{"message":{"content":"lo \xc3',
    b'\xa9 \xe2\x9c\x93"},"done":false}\n',
    b'{"message":{"content":""},"done":true,"done_reason":"stop"}\n',
]
ANSWER = 'Hello é ✓'
STREAM_HEAD = b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nConnection: close\r\n\r\n'
# About 64 KB each: data lines with no blank line between them, text with no newline, and comments only.
FLOOD = (b'data: ' + b'B' * 4000 + b'\n') * 16
NO_NEWLINE = b'A' * 65536
NOISE = b': keep-alive\n\n' * 4096


def changed_keys(key):
    """The key reversed, in base64, split by spaces and by a dot, as some error messages echo it."""
    return [key[::-1], base64.b64encode(key.encode()).decode(), ' '.join(key), key[:6] + '.' + key[6:]]


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    @property
    def fake(self):
        return self.server.fake

    def record(self, body=None):
        self.fake.requests.append(dict(method=self.command, path=self.path, headers=dict(self.headers.items()), body=body))

    def reply(self, status, payload, content_type='application/json'):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def gone(self):
        try:
            readable, _, _ = select.select([self.connection], [], [], 0)
            return bool(readable) and self.connection.recv(1, socket.MSG_PEEK) == b''
        except OSError:
            return True

    def ended(self):
        self.fake.closed.append(time.monotonic())
        self.close_connection = True

    def drip(self, head, byte):
        """Send head, then one byte at a time until the client goes away or `release` is set."""
        try:
            self.connection.sendall(head)
            while not self.fake.release.wait(self.fake.delay or 0.2) and not self.gone():
                self.connection.sendall(byte)
        except OSError:
            pass
        self.ended()

    def flood(self, block, start=b''):
        """Send block after block, up to 64 MB, until the client goes away."""
        sent = 0
        try:
            self.connection.sendall(STREAM_HEAD + start)
            while sent < 64 * 1024 * 1024 and not self.gone():
                self.connection.sendall(block)
                sent += len(block)
        except OSError:
            pass
        self.fake.sent = sent
        self.ended()

    def special(self):
        """Statuses, redirects and slow answers that every route can answer with. Returns True when it answered."""
        mode = self.fake.mode
        key = self.headers.get('Authorization', '').removeprefix('Bearer ')
        if mode == 'status':
            # Echo the Authorization header, as some providers do in their error messages.
            self.reply(self.fake.status, {'error': {'message': 'Bad credentials: ' + self.headers.get('Authorization', '')}})
            return True
        if mode == 'echo':
            self.reply(self.fake.status, {'error': {'message': 'Bad key: ' + ' / '.join(changed_keys(key))}})
            return True
        if mode == 'slowhead':
            self.drip(b'HTTP/1.1 200 OK\r\nX-Slow: ', b'a')
            return True
        if mode == 'slowerror':
            self.drip(b'HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nContent-Length: 4096\r\n\r\n', b' ')
            return True
        if mode == 'empty':
            self.reply(200, b'')
            return True
        if mode == 'html':
            self.reply(200, b'<html>proxy error</html>', 'text/html')
            return True
        if mode == 'redirect':
            self.send_response(302)
            self.send_header('Location', self.fake.redirect_to)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return True
        return False

    def do_GET(self):
        self.record()
        if self.special():
            return
        if self.path == '/api/tags':
            return self.reply(200, {'models': [{'name': 'qwen2.5-coder:7b'}, {'name': 'llama3.2:1b'}]})
        if self.fake.mode == 'slowbody':
            return self.drip(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 100000\r\n\r\n{"data":[', b' ')
        if self.path == '/v1/models':
            return self.reply(200, {'object': 'list', 'data': [{'id': 'fake-model'}, {'id': 'fake-model-2'}]})
        self.reply(404, {'error': 'not found'})

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        body = json.loads(self.rfile.read(length) or b'null')
        self.record(body)
        if self.special():
            return
        ollama = self.path == '/api/chat'
        if not ollama and self.path != '/v1/chat/completions':
            return self.reply(404, {'error': 'not found'})
        mode = self.fake.mode
        if mode == 'flood':
            return self.flood(FLOOD)
        if mode == 'nonl':
            return self.flood(NO_NEWLINE, b'' if ollama else b'data: ')
        if mode == 'noise':
            return self.flood(b'{}\n' * 16384 if ollama else NOISE)
        if mode == 'echostream':
            key = self.headers.get('Authorization', '').removeprefix('Bearer ')
            message = 'In-stream: ' + ' / '.join(changed_keys(key))
            self.connection.sendall(STREAM_HEAD + b'data: ' + json.dumps({'error': {'message': message}}).encode() + b'\n\n')
            return self.ended()
        if mode == 'plain':
            # Some servers ignore stream: one JSON answer, over several lines.
            answer = {'model': 'm', 'message': {'role': 'assistant', 'content': ANSWER}, 'done': True} if ollama else \
                {'object': 'chat.completion', 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': ANSWER}}]}
            return self.reply(200, json.dumps(answer, indent=2).encode())
        if mode == 'slow':
            time.sleep(self.fake.delay)
        self.send_response(200)
        self.send_header('Content-Type', 'application/x-ndjson' if ollama else 'text/event-stream')
        self.end_headers()
        if mode == 'endless':
            return self.endless(ollama)
        if mode == 'early':
            self.wfile.write(NDJSON_PIECES[0].split(b'\n')[0] + b'\n' if ollama else SSE_PIECES[2] + b'\n')
            return
        if mode == 'midstream':
            first = NDJSON_PIECES[0].split(b'\n')[0] + b'\n' if ollama else SSE_PIECES[2] + b'\n'
            error = b'{"error":"model crashed"}\n' if ollama else b'data: {"error":{"message":"model crashed"}}\n\n'
            self.wfile.write(first + error)
            return
        for piece in NDJSON_PIECES if ollama else SSE_PIECES:
            self.wfile.write(piece)
            self.wfile.flush()
            time.sleep(0.02)

    def endless(self, ollama):
        sock = self.connection
        while True:
            try:
                readable, _, _ = select.select([sock], [], [], 0)
                if readable and sock.recv(1, socket.MSG_PEEK) == b'':
                    break
                line = (b'{"message":{"content":"x"},"done":false}\n' if ollama
                        else b'data: {"choices":[{"delta":{"content":"x"}}]}\n\n')
                sock.sendall(line)
            except OSError:
                break
            time.sleep(0.05)
        self.fake.closed.append(time.monotonic())
        self.close_connection = True


class FakeLLM:
    def __init__(self):
        self.requests = []
        self.closed = []
        self.mode = 'ok'
        self.status = 401
        self.redirect_to = ''
        self.delay = 0
        self.sent = 0
        self.release = threading.Event()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
        self.server.daemon_threads = True
        self.server.fake = self
        self.port = self.server.server_address[1]
        self.url = f'http://127.0.0.1:{self.port}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def reset(self, mode='ok'):
        self.mode = mode
        self.delay = 0
        self.sent = 0
        self.requests.clear()
        self.closed.clear()
        self.release.clear()

    def stop(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
