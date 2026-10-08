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

CONNECT_TIMEOUT = 10
# Local models can take a while to load before the first token.
FIRST_BYTE_TIMEOUT = 90
CHUNK_TIMEOUT = 60
TOTAL_TIMEOUT = 180
MAX_ANSWER_CHARS = 64000
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

class SSEParser:
    """Server-sent events: returns the data of each completed event."""

    def __init__(self):
        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self.buffer = ''
        self.data = []

    def _line(self, line):
        if line == '':
            if self.data:
                event = '\n'.join(self.data)
                self.data = []
                return event
            return None
        if line.startswith(':'):
            return None
        field, _, value = line.partition(':')
        if value.startswith(' '):
            value = value[1:]
        if field == 'data':
            self.data.append(value)
        return None

    def feed(self, chunk):
        self.buffer += self.decoder.decode(chunk)
        events = []
        while True:
            match = re.search(r'\r\n|\r|\n', self.buffer)
            # A lone \r at the end may be the first half of \r\n.
            if not match or (match.group() == '\r' and match.end() == len(self.buffer)):
                break
            line = self.buffer[:match.start()]
            self.buffer = self.buffer[match.end():]
            event = self._line(line)
            if event is not None:
                events.append(event)
        return events

    def close(self):
        """Events still open when the stream ended."""
        events = self.feed(b'\n\n') if self.buffer or self.data else []
        return events


class NDJSONParser:
    """One JSON object per line, as Ollama streams them."""

    def __init__(self):
        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self.buffer = ''

    def feed(self, chunk):
        self.buffer += self.decoder.decode(chunk)
        lines = self.buffer.split('\n')
        self.buffer = lines.pop()
        return [obj for obj in map(_json_line, lines) if obj is not None]

    def close(self):
        rest, self.buffer = self.buffer, ''
        obj = _json_line(rest)
        return [obj] if obj is not None else []


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
        content = delta.get('content') if isinstance(delta, dict) else None
        if isinstance(content, str) and content:
            events.append(('delta', content))
        break
    return events


def ollama_events(obj):
    if not isinstance(obj, dict):
        return []
    if obj.get('error'):
        return [('error', _error_text(obj['error']))]
    events = []
    message = obj.get('message')
    content = message.get('content') if isinstance(message, dict) else None
    if isinstance(content, str) and content:
        events.append(('delta', content))
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
        body = dict(model=model, messages=messages, stream=stream,
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
    def __init__(self, target, on_socket):
        super().__init__(target.host, target.port, timeout=CONNECT_TIMEOUT)
        self._target = target
        self._on_socket = on_socket

    def connect(self):
        error = None
        for address in self._target.addresses:
            try:
                sock = socket.create_connection((address, self._target.port), CONNECT_TIMEOUT)
                break
            except OSError as exc:
                error = exc
        else:
            raise error or OSError('No address')
        self._on_socket(sock)
        if self._target.scheme == 'https':
            sock = tls().wrap_socket(sock, server_hostname=self._target.host)
            self._on_socket(sock)
        self.sock = sock


class Upstream:
    """One request to the provider. abort() from another thread closes the socket, which ends a blocked read."""

    def __init__(self, target, key=''):
        self.target = target
        self.key = key
        self.cancelled = threading.Event()
        self._lock = threading.Lock()
        self._socks = []
        self.connection = None

    def _register(self, sock):
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
        connection = _PinnedConnection(self.target, self._register)
        self.connection = connection
        connection.connect()
        if self.cancelled.is_set():
            raise ProviderError('Stopped.')
        path = self.target.path.rstrip('/') + suffix
        connection.request(method, path or '/', body=body, headers=self.headers(protocol, body))
        # getresponse() hands the socket to the response, so keep it here to change the timeout afterwards.
        sock = connection.sock
        sock.settimeout(FIRST_BYTE_TIMEOUT)
        response = connection.getresponse()
        sock.settimeout(CHUNK_TIMEOUT)
        return response

    def error_for(self, response):
        """A plain message for a response that is not 200. The body is read only to find the provider's message."""
        host = self.target.label
        status = response.status
        if 300 <= status < 400:
            return f'{host} answered with a redirect (HTTP {status}). Redirects are not followed. Check the base URL.'
        detail = ''
        try:
            raw = response.read(MAX_ERROR_BYTES)
            obj = _json_line(raw.decode('utf-8', 'replace'))
            if isinstance(obj, dict) and obj.get('error'):
                detail = _error_text(obj['error'])
            elif isinstance(obj, dict) and obj.get('message'):
                detail = _error_text(obj['message'])
        except (OSError, ValueError, http.client.HTTPException):
            pass
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


def run_stream(upstream, protocol, provider, model, messages, max_tokens, events, deadline=None):
    """Read one streamed answer into the events queue as ('delta', text), then ('done', info) or ('error', text).

    Runs on its own thread so that the request handler can watch the browser connection.
    """
    deadline = deadline or time.monotonic() + TOTAL_TIMEOUT
    suffix, body = chat_request(protocol, provider, model, messages, max_tokens)
    size = 0
    try:
        response = upstream.open('POST', suffix, protocol, body)
        if response.status != 200:
            events.put(('error', upstream.error_for(response)))
            return
        decoder = StreamDecoder(protocol)
        while True:
            if upstream.cancelled.is_set():
                return
            if time.monotonic() > deadline:
                events.put(('error', 'The answer took longer than 3 minutes and was stopped.'))
                return
            chunk = response.read1(8192)
            found = decoder.feed(chunk) if chunk else decoder.close()
            for kind, value in found:
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
        if not upstream.cancelled.is_set():
            events.put(('error', upstream.describe(exc)))
    finally:
        upstream.close()


def fetch_models(upstream, protocol):
    try:
        response = upstream.open('GET', models_path(protocol), protocol)
        if response.status != 200:
            raise ProviderError(upstream.error_for(response))
        payload = response.read(MAX_MODELS_BYTES + 1)
        if len(payload) > MAX_MODELS_BYTES:
            raise ProviderError('The model list is too large to read.')
        return parse_models(protocol, payload)
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
