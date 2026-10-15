"""A small Markdown converter for book imports, written for the standard library.

It builds ElementTree blocks. The library sanitizer then turns them into reader HTML, as it does
for EPUB chapters, so links, images, ids and classes follow the same rules for every format.
Raw HTML in the source is never passed through: tags are removed, and script and style
content is dropped. The parser scans each line once and bounds its nesting, so a crafted file
cannot make it backtrack or recurse without limit.
"""
from bisect import bisect_right
import re
import unicodedata
from xml.etree import ElementTree as ET

MAX_BLOCK_DEPTH = 12      # nested lists and quotes
MAX_INLINE_DEPTH = 8      # links and images inside link text
MAX_EMPHASIS = 16         # open emphasis markers kept at one time
MAX_NODES = 1_000_000     # elements in one document
MAX_LABEL = 1000          # characters in link text
MAX_DESTINATION = 4000    # characters in a link target

FENCE = re.compile(r' {0,3}(`{3,}|~{3,})[ \t]*([^`\s]*)')
BULLET = re.compile(r'( {0,3})([-+*])( {1,4}|\t|$)')
ORDERED = re.compile(r'( {0,3})(\d{1,9})([.)])( {1,4}|\t|$)')
TABLE_CELL = re.compile(r':?-+:?')
SPECIAL = re.compile(r'[\\`\n!\[<*_~]')
TAG = re.compile(r'</?([A-Za-z][A-Za-z0-9-]{0,40})(?:\s[^<>]{0,2000})?/?>')
AUTOLINK = re.compile(r'<(https?://[^\s<>]{1,2000})>')
DROPPED_BLOCKS = ('script', 'style', 'textarea', 'template', 'noscript')
ESCAPABLE = set('\\`*_{}[]()#+-.!|~<>"\'')
LANGUAGE = re.compile(r'^[A-Za-z0-9_+#.-]{1,40}$')


def leading_spaces(line):
    return len(line) - len(line.lstrip(' '))


def is_rule(line):
    """A thematic break: three or more of the same - * or _, with optional spaces."""
    if leading_spaces(line) > 3:
        return False
    compact = line.replace(' ', '')
    return len(compact) >= 3 and compact[0] in '-*_' and compact == compact[0] * len(compact)


def is_table_rule(line):
    """The |---|:---:| row under a table header."""
    stripped = line.strip()
    if leading_spaces(line) > 3 or '-' not in stripped:
        return False
    inner = stripped[1:] if stripped.startswith('|') else stripped
    inner = inner[:-1] if inner.endswith('|') else inner
    parts = [part.strip() for part in inner.split('|')]
    return (len(parts) > 1 or '|' in stripped) and all(TABLE_CELL.fullmatch(part) for part in parts)


def reference_definition(line):
    """Parse a [label]: url definition. Returns (label, url) or None. The title is ignored."""
    stripped = line.lstrip(' ')
    if leading_spaces(line) > 3 or not stripped.startswith('['):
        return None
    end = stripped.find(']:', 1, 202)
    if end < 2 or '[' in stripped[1:end] or ']' in stripped[1:end]:
        return None
    rest = stripped[end + 2:].split(None, 1)
    if not rest:
        return None
    url = rest[0]
    if url.startswith('<') and url.endswith('>'):
        url = url[1:-1]
    if not url or len(url) > MAX_DESTINATION or '<' in url or '>' in url:
        return None
    if len(rest) > 1 and rest[1].strip()[:1] not in ('"', "'", '('):
        return None
    return stripped[1:end], url


class TooLarge(ValueError):
    pass


class Builder:
    """Counts the elements one document creates."""
    def __init__(self, limit=None):
        self.count = 0
        self.limit = limit or MAX_NODES

    def element(self, tag, attrib=None):
        self.count += 1
        if self.count > self.limit:
            raise TooLarge(f'This file has more than {self.limit:,} elements, which is over the import limit.')
        return ET.Element(tag, attrib or {})

    def child(self, parent, tag, attrib=None):
        node = self.element(tag, attrib)
        parent.append(node)
        return node


def append_text(parent, text):
    if not text:
        return
    if len(parent):
        parent[-1].tail = (parent[-1].tail or '') + text
    else:
        parent.text = (parent.text or '') + text


def heading_slug(text, used):
    """A GitHub-style id for a heading, unique within the document."""
    slug = unicodedata.normalize('NFKC', text).strip().lower()
    slug = re.sub(r'[^\w\- ]', '', slug).replace(' ', '-')[:80] or 'section'
    candidate, n = slug, 1
    while candidate in used:
        candidate = f'{slug}-{n}'; n += 1
    used.add(candidate)
    return candidate


def code_block(builder, code, language='', label=''):
    """A code block with an optional language label, shared with notebooks."""
    language = language if LANGUAGE.fullmatch(language or '') else ''
    label = label or language
    if not label:
        pre = builder.element('pre')
        builder.child(pre, 'code').text = code
        return pre
    cell = builder.element('div', {'class': 'code-cell'})
    builder.child(cell, 'p', {'class': 'code-label'}).text = label
    pre = builder.child(cell, 'pre')
    code_node = builder.child(pre, 'code', {'class': 'language-' + language} if language else None)
    code_node.text = code
    return cell


class Markdown:
    def __init__(self, builder=None):
        self.builder = builder or Builder()
        self.references = {}
        self.slugs = set()

    # Block structure -------------------------------------------------------------------------

    def convert(self, text):
        """Return a list of block elements for one Markdown document."""
        text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\x00', '\ufffd')
        lines = [line.expandtabs(4) for line in text.split('\n')]
        lines = self.collect_references(lines)
        return self.blocks(lines, 0)

    def collect_references(self, lines):
        """Read [label]: url definitions first, so links can use them before they are defined."""
        kept, fence = [], None
        for line in lines:
            match = FENCE.match(line)
            if fence:
                if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence) and not match.group(2):
                    fence = None
                kept.append(line)
                continue
            if match:
                fence = match.group(1)
                kept.append(line)
                continue
            reference = reference_definition(line)
            if reference:
                self.references.setdefault(reference[0].strip().casefold(), reference[1])
                continue
            kept.append(line)
        return kept

    def blocks(self, lines, depth):
        out, i, n = [], 0, len(lines)
        b = self.builder
        while i < n:
            line = lines[i]
            stripped = line.lstrip(' ')
            indent = len(line) - len(stripped)
            if not stripped.strip():
                i += 1
                continue
            fence = FENCE.match(line)
            if fence:
                marker, language = fence.group(1), fence.group(2)
                body, i = [], i + 1
                while i < n:
                    close = FENCE.match(lines[i])
                    if close and close.group(1)[0] == marker[0] and len(close.group(1)) >= len(marker) and not close.group(2):
                        i += 1
                        break
                    body.append(lines[i][min(indent, len(lines[i]) - len(lines[i].lstrip(' '))):])
                    i += 1
                out.append(code_block(b, '\n'.join(body), language))
                continue
            if indent >= 4:
                body = []
                while i < n and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip(' ')) >= 4):
                    body.append(lines[i][4:])
                    i += 1
                while body and not body[-1].strip():
                    body.pop()
                out.append(code_block(b, '\n'.join(body)))
                continue
            heading = self.atx_heading(line)
            if heading:
                out.append(self.heading(*heading))
                i += 1
                continue
            if is_rule(line):
                out.append(b.element('hr'))
                i += 1
                continue
            lowered = stripped.lower()
            dropped = next((tag for tag in DROPPED_BLOCKS if lowered.startswith('<' + tag)), None)
            if dropped or stripped.startswith('<!--'):
                closing = '-->' if not dropped else f'</{dropped}'
                while i < n and closing not in lines[i].lower():
                    i += 1
                i += 1
                continue
            if stripped.startswith('>') and depth < MAX_BLOCK_DEPTH:
                quoted = []
                while i < n and lines[i].lstrip(' ').startswith('>') and len(lines[i]) - len(lines[i].lstrip(' ')) < 4:
                    rest = lines[i].lstrip(' ')[1:]
                    quoted.append(rest[1:] if rest.startswith(' ') else rest)
                    i += 1
                quote = b.element('blockquote')
                quote.extend(self.blocks(quoted, depth + 1))
                out.append(quote)
                continue
            item = self.list_marker(line)
            if item and depth < MAX_BLOCK_DEPTH:
                element, i = self.list_block(lines, i, depth)
                out.append(element)
                continue
            if '|' in line and i + 1 < n and is_table_rule(lines[i + 1]):
                element, i = self.table(lines, i)
                if element is not None:
                    out.append(element)
                    continue
            # A paragraph runs until a blank line or the start of another block.
            body = [stripped]
            i += 1
            while i < n:
                following = lines[i]
                if not following.strip():
                    break
                setext = following.strip()
                if setext and set(setext) <= {'='} or (set(setext) <= {'-'} and len(setext) >= 2):
                    out.append(self.heading(1 if setext[0] == '=' else 2, ' '.join(body)))
                    body = []
                    i += 1
                    break
                if self.interrupts(following):
                    break
                body.append(following.lstrip(' '))
                i += 1
            if body:
                paragraph = b.element('p')
                self.inline(paragraph, '\n'.join(body), 0)
                out.append(paragraph)
        return out

    def interrupts(self, line):
        stripped = line.lstrip(' ')
        if len(line) - len(stripped) >= 4:
            return False
        return bool(FENCE.match(line) or self.atx_heading(line) or is_rule(line) or stripped.startswith('>')
                    or BULLET.match(line) or ORDERED.match(line) and ORDERED.match(line).group(2) == '1')

    @staticmethod
    def atx_heading(line):
        stripped = line.lstrip(' ')
        if len(line) - len(stripped) >= 4 or not stripped.startswith('#'):
            return None
        level = len(stripped) - len(stripped.lstrip('#'))
        rest = stripped[level:]
        if level > 6 or (rest and rest[0] not in ' \t'):
            return None
        content = rest.strip()
        if content.endswith('#'):
            trimmed = content.rstrip('#')
            if not trimmed or trimmed[-1] in ' \t':
                content = trimmed.strip()
        return level, content

    def heading(self, level, text):
        node = self.builder.element(f'h{level}')
        self.inline(node, text, 0)
        node.set('id', heading_slug(''.join(node.itertext()), self.slugs))
        return node

    @staticmethod
    def list_marker(line):
        match = BULLET.match(line)
        if match:
            return False, match.group(2), len(match.group(0)) if match.group(3) else len(match.group(0)) + 1, None
        match = ORDERED.match(line)
        if match:
            width = len(match.group(0)) if match.group(4) else len(match.group(0)) + 1
            return True, match.group(3), width, int(match.group(2))
        return None

    def list_block(self, lines, i, depth):
        ordered, delimiter, _, start = self.list_marker(lines[i])
        b = self.builder
        element = b.element('ol' if ordered else 'ul')
        if ordered and start != 1:
            element.set('start', str(start))
        items, n, gap = [], len(lines), False
        while i < n:
            if not lines[i].strip():
                # Blank lines between two items keep the list going and make it loose.
                j = i
                while j < n and not lines[j].strip():
                    j += 1
                following = self.list_marker(lines[j]) if j < n else None
                if not following or following[0] != ordered or following[1] != delimiter:
                    break
                gap, i = True, j
            marker = self.list_marker(lines[i])
            if not marker or marker[0] != ordered or marker[1] != delimiter:
                break
            width = marker[2]
            first = lines[i][width:] if len(lines[i]) > width else ''
            body, i = [first], i + 1
            while i < n:
                line = lines[i]
                if not line.strip():
                    # A blank line continues the item only if the next text is indented under it.
                    j = i
                    while j < n and not lines[j].strip():
                        j += 1
                    if j < n and len(lines[j]) - len(lines[j].lstrip(' ')) >= width:
                        body.extend([''] * (j - i))
                        i = j
                        continue
                    break
                indent = len(line) - len(line.lstrip(' '))
                if indent >= width:
                    body.append(line[width:])
                elif self.list_marker(line) or self.interrupts(line) or (body and not body[-1].strip()):
                    break
                else:
                    body.append(line.strip(' '))  # a lazy continuation line
                i += 1
            items.append(body)
        loose = gap or any('' in body[:-1] for body in items)
        for body in items:
            item = b.child(element, 'li')
            blocks = self.blocks(body, depth + 1)
            if not loose and blocks and blocks[0].tag == 'p':
                # A tight list item holds its text directly, without a paragraph.
                first = blocks.pop(0)
                item.text = first.text
                item.extend(list(first))
            item.extend(blocks)
        return element, i

    def table(self, lines, i):
        def cells(line):
            line = line.strip()
            if line.startswith('|'):
                line = line[1:]
            if line.endswith('|') and not line.endswith('\\|'):
                line = line[:-1]
            parts, current, escaped = [], [], False
            for char in line:
                if char == '|' and not escaped:
                    parts.append(''.join(current)); current = []
                else:
                    current.append(char)
                escaped = char == '\\' and not escaped
            parts.append(''.join(current))
            return [part.strip() for part in parts]
        header = cells(lines[i])
        if len(header) != len(cells(lines[i + 1])) or len(header) > 64:
            return None, i
        b = self.builder
        table = b.element('table')
        row = b.child(b.child(table, 'thead'), 'tr')
        for text in header:
            self.inline(b.child(row, 'th'), text, 0)
        body = b.child(table, 'tbody')
        i += 2
        while i < len(lines) and lines[i].strip() and '|' in lines[i]:
            row = b.child(body, 'tr')
            values = cells(lines[i])[:len(header)]
            for text in values + [''] * (len(header) - len(values)):
                self.inline(b.child(row, 'td'), text, 0)
            i += 1
        return table, i

    # Inline content ----------------------------------------------------------------------------

    def inline(self, parent, text, depth, in_link=False):
        """Add the inline content of `text` to parent: code, emphasis, links, images and breaks."""
        tokens = self.tokens(text, depth, in_link)
        for node in self.emphasis(tokens):
            if isinstance(node, str):
                append_text(parent, node)
            else:
                parent.append(node)

    def tokens(self, text, depth, in_link):
        b = self.builder
        n = len(text)
        lowered = text.lower()
        brackets = matching(text, '[', ']')
        parens = matching(text, '(', ')')
        ticks = backtick_runs(text)
        out, buffer, i = [], [], 0

        def flush():
            if buffer:
                out.append(''.join(buffer)); buffer.clear()

        while i < n:
            special = SPECIAL.search(text, i)
            if not special:
                buffer.append(text[i:])
                break
            if special.start() > i:
                buffer.append(text[i:special.start()])
                i = special.start()
            char = text[i]
            if char == '\\' and i + 1 < n:
                if text[i + 1] == '\n':
                    flush(); out.append(b.element('br')); i += 2; continue
                if text[i + 1] in ESCAPABLE:
                    buffer.append(text[i + 1]); i += 2; continue
            if char == '`':
                length = run_length(text, i, '`')
                end = next_run(ticks, length, i + length)
                if end is None:
                    buffer.append('`' * length); i += length; continue
                code = text[i + length:end].replace('\n', ' ')
                if len(code) > 2 and code[0] == ' ' and code[-1] == ' ' and code.strip():
                    code = code[1:-1]
                flush(); node = b.element('code'); node.text = code; out.append(node)
                i = end + length
                continue
            if char == '\n':
                line = ''.join(buffer); buffer.clear()
                kept = line.rstrip(' ')
                if kept:
                    out.append(kept)
                out.append(b.element('br') if len(line) - len(kept) >= 2 else '\n')
                i += 1
                continue
            if char == '!' and i + 1 < n and text[i + 1] == '[' and depth < MAX_INLINE_DEPTH:
                link = self.link(text, i + 1, brackets, parens)
                if link:
                    label, destination, end = link
                    flush()
                    out.append(b.element('img', {'src': destination, 'alt': plain(label)[:300] or 'Image'}))
                    i = end
                    continue
            if char == '[' and not in_link and depth < MAX_INLINE_DEPTH:
                link = self.link(text, i, brackets, parens)
                if link:
                    label, destination, end = link
                    flush()
                    node = b.element('a', {'href': destination})
                    self.inline(node, label, depth + 1, in_link=True)
                    out.append(node)
                    i = end
                    continue
            if char == '<':
                match = AUTOLINK.match(text, i)
                if match and not in_link:
                    flush()
                    node = b.element('a', {'href': match.group(1)}); node.text = match.group(1); out.append(node)
                    i = match.end()
                    continue
                if text.startswith('<!--', i):
                    end = text.find('-->', i + 4)
                    i = n if end < 0 else end + 3
                    continue
                match = TAG.match(text, i)
                if match:
                    name = match.group(1).lower()
                    i = match.end()
                    if name in DROPPED_BLOCKS and not match.group(0).startswith('</'):
                        end = lowered.find(f'</{name}', i)
                        i = n if end < 0 else (lowered.find('>', end) + 1 or n)
                    elif name == 'br':
                        flush(); out.append(b.element('br'))
                    continue
            if char in '*_~':
                length = run_length(text, i, char)
                before = text[i - 1] if i else ' '
                after = text[i + length] if i + length < n else ' '
                opens = not after.isspace()
                closes = not before.isspace()
                if char == '_':
                    opens = opens and not before.isalnum()
                    closes = closes and not after.isalnum()
                if char == '~' and length != 2:
                    opens = closes = False
                if opens or closes:
                    flush(); out.append(Delimiter(char, length, opens, closes)); i += length
                    continue
                buffer.append(char * length); i += length
                continue
            buffer.append(char)
            i += 1
        flush()
        return out

    def link(self, text, start, brackets, parens):
        """Parse [label](url) or [label][reference] at start. Returns (label, url, end) or None."""
        close = brackets.get(start)
        if close is None or close - start > MAX_LABEL:
            return None
        after = close + 1
        if after < len(text) and text[after] == '(':
            end = parens.get(after)
            if end is None or end - after > MAX_DESTINATION:
                return None
            inside = text[after + 1:end].strip()
            if inside.startswith('<') and '>' in inside:
                destination = inside[1:inside.index('>')]
            else:
                destination = inside.split(None, 1)[0] if inside else ''
            return text[start + 1:close], destination, end + 1
        if not self.references:
            return None
        label = text[start + 1:close]
        if after < len(text) and text[after] == '[':
            end = brackets.get(after)
            if end is not None and end - after <= MAX_LABEL:
                key = (text[after + 1:end] or label).strip().casefold()
                if key in self.references:
                    return label, self.references[key], end + 1
        key = label.strip().casefold()
        if key in self.references:
            return label, self.references[key], after
        return None

    def emphasis(self, tokens):
        """Match * _ ~~ delimiters with a bounded stack. Unmatched ones stay as text."""
        stack = [[None, []]]
        for token in tokens:
            if not isinstance(token, Delimiter):
                stack[-1][1].append(token)
                continue
            opener_index = None
            if token.closes:
                for index in range(len(stack) - 1, 0, -1):
                    if stack[index][0].char == token.char:
                        opener_index = index
                        break
            if opener_index is not None:
                while len(stack) - 1 > opener_index:
                    delimiter, children = stack.pop()
                    stack[-1][1].append(delimiter.char * delimiter.length)
                    stack[-1][1].extend(children)
                opener, children = stack.pop()
                if token.char == '~':
                    tag = 's'
                    used = 2
                else:
                    used = 2 if opener.length >= 2 and token.length >= 2 else 1
                    tag = 'strong' if used == 2 else 'em'
                node = self.builder.element(tag)
                for child in children:
                    if isinstance(child, str):
                        append_text(node, child)
                    else:
                        node.append(child)
                if opener.length > used:
                    stack[-1][1].append(token.char * (opener.length - used))
                stack[-1][1].append(node)
                if token.length > used:
                    stack[-1][1].append(token.char * (token.length - used))
            elif token.opens and len(stack) <= MAX_EMPHASIS:
                stack.append([token, []])
            else:
                stack[-1][1].append(token.char * token.length)
        while len(stack) > 1:
            delimiter, children = stack.pop()
            stack[-1][1].append(delimiter.char * delimiter.length)
            stack[-1][1].extend(children)
        return stack[0][1]


class Delimiter:
    __slots__ = ('char', 'length', 'opens', 'closes')

    def __init__(self, char, length, opens, closes):
        self.char, self.length, self.opens, self.closes = char, length, opens, closes


def run_length(text, i, char):
    j = i
    while j < len(text) and text[j] == char:
        j += 1
    return j - i


def backtick_runs(text):
    """Start positions of each backtick run, grouped by run length, in one pass."""
    runs, i, n = {}, 0, len(text)
    while i < n:
        i = text.find('`', i)
        if i < 0:
            break
        length = run_length(text, i, '`')
        runs.setdefault(length, []).append(i)
        i += length
    return runs


def next_run(runs, length, position):
    starts = runs.get(length, [])
    index = bisect_right(starts, position - 1)
    return starts[index] if index < len(starts) else None


def matching(text, opening, closing):
    """Positions of matching bracket pairs, found with one stack pass. Escaped brackets are skipped."""
    pairs, stack, i, n = {}, [], 0, len(text)
    while i < n:
        char = text[i]
        if char == '\\':
            i += 2
            continue
        if char == opening:
            stack.append(i)
            if len(stack) > 1000:
                stack.pop(0)
        elif char == closing and stack:
            pairs[stack.pop()] = i
        i += 1
    return pairs


def plain(text):
    """Text of a link label or image alt, without Markdown punctuation."""
    return re.sub(r'[*_`~\[\]]', '', text).strip()


def markdown_blocks(text, builder=None):
    return Markdown(builder).convert(text)
