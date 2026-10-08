"""Provider adapters for the optional AI assistant: request bodies, stream parsers and one upstream connection.

Standard library only. Upstream calls use http.client, which never follows redirects and ignores proxy
variables. The connection goes to an address that the URL policy in assistant.py already checked.
"""
import codecs
import http.client
import json
import re
import socket
import ssl
import threading
import time

# Seconds. Socket timeouts limit each read; the deadlines below limit wall-clock time, so a provider that sends
# one byte at a time cannot hold a request open.
CONNECT_TIMEOUT = 10
# Local models can take a while to load before the first token.
FIRST_BYTE_TIMEOUT = 90
CHUNK_TIMEOUT = 60
ERROR_BODY_TIMEOUT = 10
TOTAL_TIMEOUT = 180
TEST_TIMEOUT = 60
MODELS_TIMEOUT = 30
# How often the deadline thread looks at the clock.
WATCH_INTERVAL = 0.2
MAX_ANSWER_CHARS = 64000
# Limits on what the provider sends, beyond the answer text: one line, one event, and all bytes of one answer.
MAX_LINE_CHARS = 256 * 1024
MAX_EVENT_CHARS = 256 * 1024
MAX_UPSTREAM_BYTES = 4 * 1024 * 1024
LINE_TOO_LONG = 'The provider sent a line longer than 256 KB, so the answer was stopped.'
EVENT_TOO_LONG = 'The provider sent an event larger than 256 KB, so the answer was stopped.'
TOO_MANY_BYTES = 'The provider sent more than 4 MB for one answer, so it was stopped.'
MAX_ERROR_BYTES = 4096
MAX_MODELS_BYTES = 8 * 1024 * 1024
USER_AGENT = 'EngineeringWorkshop'
# Ollama cuts the start of a prompt that is longer than its context window, so the server sets the window.
OLLAMA_CONTEXT = 16384


class ProviderError(Exception):
    """A message that is safe to show and to log. It never contains the API key."""


def _tls_context():
    context = ssl.create_default_context()
    if not context.cert_store_stats().get('x509_ca'):
        # Some Python builds ship without a system CA path. certifi is present in the full install.
        try:
            import certifi
            context.load_verify_locations(certifi.where())
        except (ImportError, OSError):
            pass
    return context


TLS = None
TLS_LOCK = threading.Lock()


def tls():
    global TLS
    with TLS_LOCK:
        if TLS is None:
            TLS = _tls_context()
        return TLS


# ---- Stream parsers. Both accept bytes in any split, including inside a UTF-8 character. ----

class StreamTooLarge(ProviderError):
    """The provider sent a line, an event or an answer above the size limits."""


class _Lines:
    """Split streamed text into lines. Only new text is searched, and an unfinished line is kept as parts, so
    each byte is looked at once. A line longer than MAX_LINE_CHARS raises StreamTooLarge."""

    def __init__(self, end):
        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self.end = end
        self.parts = []
        self.size = 0
        # A line that ended with \r at the end of a chunk: a \n at the start of the next chunk belongs to it.
        self.skip_lf = False

    def _add(self, piece):
        if piece:
            self.size += len(piece)
            if self.size > MAX_LINE_CHARS:
                raise StreamTooLarge(LINE_TOO_LONG)
            self.parts.append(piece)

    def feed(self, chunk, final=False):
        text = self.decoder.decode(chunk, final)
        lines, pos, size = [], 0, len(text)
        if self.skip_lf and text:
            self.skip_lf = False
            if text[0] == '\n':
                pos = 1
        while pos < size:
            match = self.end.search(text, pos)
            if not match:
                self._add(text[pos:])
                break
            self._add(text[pos:match.start()])
            lines.append(''.join(self.parts))
            self.parts, self.size = [], 0
            pos = match.end()
            if match.group() == '\r':
                if pos == size:
                    self.skip_lf = True
                elif text[pos] == '\n':
                    pos += 1
        return lines

    def close(self):
        """The lines still open when the stream ended."""
        lines = self.feed(b'', final=True)
        if self.parts:
            lines.append(''.join(self.parts))
            self.parts, self.size = [], 0
        return lines


class SSEParser:
    """Server-sent events: returns the data of each completed event."""

    def __init__(self):
        self.lines = _Lines(re.compile('[\r\n]'))
        self.data = []
        self.size = 0

    def _line(self, line):
        if line == '':
            if self.data:
                event = '\n'.join(self.data)
                self.data, self.size = [], 0
                return event
            return None
        if line.startswith(':'):
            return None
        field, _, value = line.partition(':')
        if value.startswith(' '):
            value = value[1:]
        if field == 'data':
            self.size += len(value) + 1
            if self.size > MAX_EVENT_CHARS:
                raise StreamTooLarge(EVENT_TOO_LONG)
            self.data.append(value)
        return None

    def _events(self, lines):
        return [event for event in map(self._line, lines) if event is not None]

    def feed(self, chunk):
        return self._events(self.lines.feed(chunk))

    def close(self):
        """Events still open when the stream ended."""
        events = self._events(self.lines.close())
        if self.data:
            events.append(self._line(''))
        return events


class NDJSONParser:
    """One JSON object per line, as Ollama streams them."""

    def __init__(self):
        self.lines = _Lines(re.compile('\n'))

    def feed(self, chunk):
        return [obj for obj in map(_json_line, self.lines.feed(chunk)) if obj is not None]

    def close(self):
        return [obj for obj in map(_json_line, self.lines.close()) if obj is not None]


def _json_line(line):
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except ValueError:
        return None


def _error_text(error):
    if isinstance(error, dict):
        error = error.get('message') or error.get('error') or error.get('code') or ''
    return str(error)[:300]


def openai_events(data):
    """Turn the data of one OpenAI-style event into ('delta', text), ('done', None) or ('error', text)."""
    if data.strip() == '[DONE]':
        return [('done', None)]
    obj = _json_line(data)
    if not isinstance(obj, dict):
        return []
    if obj.get('error'):
        return [('error', _error_text(obj['error']))]
    events = []
    for choice in obj.get('choices') or []:
        if not isinstance(choice, dict):
            continue
        delta = choice.get('delta') or choice.get('message') or {}
        if not isinstance(delta, dict):
            break
        content = delta.get('content')
        if isinstance(content, str) and content:
            events.append(('delta', content))
        elif delta.get('reasoning') or delta.get('reasoning_content'):
            # Reasoning text is not shown, only that the model is still working.
            events.append(('thinking', None))
        break
    return events


def ollama_events(obj):
    if not isinstance(obj, dict):
        return []
    if obj.get('error'):
        return [('error', _error_text(obj['error']))]
    events = []
    message = obj.get('message') if isinstance(obj.get('message'), dict) else {}
    content = message.get('content')
    if isinstance(content, str) and content:
        events.append(('delta', content))
    elif message.get('thinking'):
        events.append(('thinking', None))
    if obj.get('done') is True:
        events.append(('done', None))
    return events


class StreamDecoder:
    """Bytes in, ('delta' | 'done' | 'error', value) events out, for one protocol."""

    def __init__(self, protocol):
        self.protocol = protocol
        self.parser = NDJSONParser() if protocol == 'ollama' else SSEParser()

    def _events(self, items):
        convert = ollama_events if self.protocol == 'ollama' else openai_events
        return [event for item in items for event in convert(item)]

    def feed(self, chunk):
        return self._events(self.parser.feed(chunk))

    def close(self):
        return self._events(self.parser.close())


# ---- Requests ----

def chat_request(protocol, provider, model, messages, max_tokens, temperature=0.3, stream=True):
    """Return (path suffix, JSON body bytes) for a chat request."""
    if protocol == 'ollama':
        # think=False asks a reasoning model for the answer only. Ollama versions without the option ignore it.
        body = dict(model=model, messages=messages, stream=stream, think=False,
                    options=dict(num_ctx=OLLAMA_CONTEXT, temperature=temperature, num_predict=max_tokens))
        return '/api/chat', json.dumps(body).encode()
    body = dict(model=model, messages=messages, stream=stream)
    if provider == 'openai':
        # OpenAI's newer models take max_completion_tokens and only their default temperature.
        body['max_completion_tokens'] = max_tokens
    else:
        body['max_tokens'] = max_tokens
        body['temperature'] = temperature
    return '/chat/completions', json.dumps(body).encode()


def models_path(protocol):
    return '/api/tags' if protocol == 'ollama' else '/models'


def parse_models(protocol, payload):
    try:
        obj = json.loads(payload)
    except ValueError:
        raise ProviderError('The provider sent a model list that could not be read.')
    items = obj.get('models') if protocol == 'ollama' and isinstance(obj, dict) else obj.get('data') if isinstance(obj, dict) else None
    if not isinstance(items, list):
        raise ProviderError('The provider sent a model list that could not be read.')
    names = set()
    for item in items:
        if isinstance(item, dict):
            name = item.get('name') or item.get('model') if protocol == 'ollama' else item.get('id')
            if isinstance(name, str) and 0 < len(name) <= 200:
                names.add(name)
    return sorted(names, key=str.lower)[:1000]


# ---- Upstream connection ----

class Target:
    """A checked provider address: the host name for TLS and Host, and the addresses that passed the policy."""

    def __init__(self, scheme, host, port, path, addresses):
        self.scheme, self.host, self.port, self.path, self.addresses = scheme, host, port, path, addresses

    @property
    def label(self):
        return self.host if self.port in (80, 443) else f'{self.host}:{self.port}'


class _PinnedConnection(http.client.HTTPConnection):
    def __init__(self, target, upstream):
        super().__init__(target.host, target.port, timeout=CONNECT_TIMEOUT)
        self._target = target
        self._upstream = upstream

    def connect(self):
        sock = error = None
        for address in self._target.addresses:
            left = self._upstream.time_left()
            if left <= 0 or self._upstream.cancelled.is_set():
                break
            try:
                sock = socket.create_connection((address, self._target.port), min(CONNECT_TIMEOUT, left))
                break
            except OSError as exc:
                error = exc
        if sock is None:
            raise error or TimeoutError('connect')
        self._upstream.register(sock)
        if self._target.scheme == 'https':
            sock = tls().wrap_socket(sock, server_hostname=self._target.host)
            self._upstream.register(sock)
        self.sock = sock


class Upstream:
    """One request to the provider. abort() from another thread closes the socket, which ends a blocked read.

    A deadline thread aborts the request when the whole call or the current step (connect, headers, error body)
    runs out of time. `expired` then holds the message to show.
    """

    def __init__(self, target, key='', timeout=TOTAL_TIMEOUT, expired_message=''):
        self.target = target
        self.key = key
        self.timeout = timeout
        self.expired_message = expired_message or f'{target.label} stopped answering. The request timed out.'
        self.expired = ''
        self.deadline = None
        self.cancelled = threading.Event()
        self._step = None
        self._lock = threading.Lock()
        self._socks = []
        self.connection = None

    def start(self):
        """Start the clock for the whole call."""
        if self.deadline is None:
            self.deadline = time.monotonic() + self.timeout
            threading.Thread(target=self._watch, daemon=True, name='assistant-deadline').start()

    def step(self, seconds=None, message=''):
        """Limit the next step to `seconds` of wall-clock time, or remove the step limit."""
        self._step = None if seconds is None else (time.monotonic() + seconds, message)

    def time_left(self):
        """Seconds until the whole call or the current step runs out."""
        ends = [end for end in (self.deadline, self._step and self._step[0]) if end]
        return min(ends) - time.monotonic() if ends else self.timeout

    def over_time(self):
        return self.deadline is not None and time.monotonic() > self.deadline

    def _watch(self):
        while not self.cancelled.wait(WATCH_INTERVAL):
            now, step = time.monotonic(), self._step
            if now > self.deadline:
                self.expired = self.expired_message
            elif step and now > step[0]:
                self.expired = step[1] or f'{self.target.label} stopped answering. The request timed out.'
            else:
                continue
            self.abort()
            return

    def register(self, sock):
        with self._lock:
            self._socks.append(sock)
            cancelled = self.cancelled.is_set()
        if cancelled:
            self._close(sock)

    @staticmethod
    def _close(sock):
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass

    def abort(self):
        with self._lock:
            self.cancelled.set()
            socks = list(self._socks)
        for sock in socks:
            self._close(sock)

    def headers(self, protocol, body=None):
        headers = {'User-Agent': USER_AGENT, 'Accept': 'application/json, text/event-stream, application/x-ndjson'}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        if self.key and protocol != 'ollama':
            headers['Authorization'] = 'Bearer ' + self.key
        return headers

    def open(self, method, suffix, protocol, body=None):
        """Send the request and return the response once its headers arrive."""
        self.start()
        host = self.target.label
        connection = _PinnedConnection(self.target, self)
        self.connection = connection
        self.step(CONNECT_TIMEOUT, f'Cannot connect to {host}. The connection timed out.')
        connection.connect()
        if self.cancelled.is_set():
            raise ProviderError(self.expired or 'Stopped.')
        path = self.target.path.rstrip('/') + suffix
        self.step(FIRST_BYTE_TIMEOUT, f'{host} did not start answering within {FIRST_BYTE_TIMEOUT} seconds.')
        # getresponse() hands the socket to the response, so keep it here to change the timeout afterwards.
        sock = connection.sock
        sock.settimeout(max(0.1, min(FIRST_BYTE_TIMEOUT, self.time_left())))
        connection.request(method, path or '/', body=body, headers=self.headers(protocol, body))
        response = connection.getresponse()
        self.step()
        sock.settimeout(CHUNK_TIMEOUT)
        return response

    def error_for(self, response):
        """A plain message for a response that is not 200. The body is read only to find the provider's message."""
        host = self.target.label
        status = response.status
        if 300 <= status < 400:
            return f'{host} answered with a redirect (HTTP {status}). Redirects are not followed. Check the base URL.'
        detail = ''
        self.step(ERROR_BODY_TIMEOUT)
        try:
            raw = response.read(MAX_ERROR_BYTES)
            obj = _json_line(raw.decode('utf-8', 'replace'))
            if isinstance(obj, dict) and obj.get('error'):
                detail = _error_text(obj['error'])
            elif isinstance(obj, dict) and obj.get('message'):
                detail = _error_text(obj['message'])
        except (OSError, ValueError, http.client.HTTPException):
            pass
        self.step()
        detail = redact(detail, self.key)
        if status in (401, 403):
            message = f'{host} refused the API key (HTTP {status}).'
        elif status == 404:
            message = f'{host} did not find this model or address (HTTP 404). Check the base URL and the model name.'
        elif status in (402, 429):
            message = f'Out of credit or rate-limited at {host} (HTTP {status}).'
        elif status >= 500:
            message = f'{host} had an error (HTTP {status}). Try again later.'
        else:
            message = f'{host} answered HTTP {status}.'
        return message + (f' It said: {detail}' if detail else '')

    def describe(self, exc):
        """A plain message for a connection failure."""
        host = self.target.label
        if self.expired:
            return self.expired
        if isinstance(exc, ProviderError):
            return str(exc)
        if isinstance(exc, (TimeoutError, socket.timeout)):
            return f'{host} stopped answering. The request timed out.'
        if isinstance(exc, ssl.SSLCertVerificationError):
            return f'Could not verify the TLS certificate of {host}.'
        if isinstance(exc, ssl.SSLError):
            return f'Could not make a secure connection to {host}.'
        if isinstance(exc, ConnectionRefusedError):
            return f'Cannot connect to {host}. Check that the provider is running and the address is right.'
        if isinstance(exc, http.client.HTTPException):
            return f'{host} sent a response that could not be read.'
        return f'Lost the connection to {host}.'

    def close(self):
        self.abort()


def run_stream(upstream, protocol, provider, model, messages, max_tokens, events):
    """Read one streamed answer into the events queue as ('delta', text), then ('done', info) or ('error', text).

    Runs on its own thread so that the request handler can watch the browser connection. Ends with an error
    when the provider sends more than the size limits or runs past the deadline.
    """
    suffix, body = chat_request(protocol, provider, model, messages, max_tokens)
    size = received = 0
    try:
        response = upstream.open('POST', suffix, protocol, body)
        if response.status != 200:
            events.put(('error', upstream.error_for(response)))
            return
        decoder = StreamDecoder(protocol)
        thinking = False
        while True:
            if upstream.over_time():
                upstream.expired = upstream.expired_message
            chunk = b'' if upstream.expired else response.read1(8192)
            # After abort() a read can return b'' as if the answer had ended, so check before using it.
            if upstream.cancelled.is_set() or upstream.expired:
                if upstream.expired:
                    events.put(('error', upstream.expired))
                return
            received += len(chunk)
            if received > MAX_UPSTREAM_BYTES:
                events.put(('error', TOO_MANY_BYTES))
                return
            found = decoder.feed(chunk) if chunk else decoder.close()
            for kind, value in found:
                if kind == 'thinking':
                    if not thinking and not size:
                        thinking = True
                        events.put(('thinking', None))
                    continue
                if kind == 'delta':
                    room = MAX_ANSWER_CHARS - size
                    if len(value) >= room:
                        events.put(('delta', value[:room]))
                        events.put(('done', {'truncated': True}))
                        return
                    size += len(value)
                events.put((kind, redact(value, upstream.key) if kind == 'error' else value))
                if kind in ('done', 'error'):
                    return
            if not chunk:
                events.put(('done', {}))
                return
    except Exception as exc:  # noqa: BLE001 - every failure becomes a message; nothing here may log the key.
        if upstream.expired or not upstream.cancelled.is_set():
            events.put(('error', upstream.describe(exc)))
    finally:
        upstream.close()


def fetch_models(upstream, protocol):
    try:
        response = upstream.open('GET', models_path(protocol), protocol)
        if response.status != 200:
            raise ProviderError(upstream.error_for(response))
        parts, size = [], 0
        while True:
            if upstream.over_time():
                upstream.expired = upstream.expired_message
            chunk = b'' if upstream.expired else response.read1(65536)
            if upstream.cancelled.is_set() or upstream.expired:
                raise ProviderError(upstream.expired or 'Stopped.')
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_MODELS_BYTES:
                raise ProviderError('The model list is too large to read.')
            parts.append(chunk)
        return parse_models(protocol, b''.join(parts))
    except ProviderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(upstream.describe(exc))
    finally:
        upstream.close()


SECRET_PATTERNS = [
    re.compile(r'Bearer\s+[A-Za-z0-9._~+/=-]+', re.I),
    re.compile(r'\bsk-[A-Za-z0-9_-]{8,}'),
    re.compile(r'\b(?:AKIA|ghp_|gho_|github_pat_|xox[abp]-|AIza)[A-Za-z0-9_-]{12,}'),
]


def redact(text, key=''):
    """Remove the configured key and strings that look like API keys."""
    if not text:
        return text
    if key and len(key) >= 4:
        text = text.replace(key, '[redacted]')
    for pattern in SECRET_PATTERNS:
        text = pattern.sub('[redacted]', text)
    return text
