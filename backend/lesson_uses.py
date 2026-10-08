"""The language constructs a lesson's starter and solution use, and where each one is taught.

Python code is read with the ast module. JavaScript is matched with regular expressions
after strings and comments are removed; the web lessons are short and written here.
Each construct links to the lesson that teaches it, or to the official documentation
when no lesson does.
"""
import ast
import re

PY_DOCS = 'https://docs.python.org/3/'
MDN = 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/'

# id, label, lesson that teaches it, documentation when no lesson does. Listed in teaching order.
PYTHON = [
    ('power', '** for powers', 'python-2', None),
    ('def', 'def and return', 'python-3', None),
    ('if', 'if, elif and else', 'python-4', None),
    ('logic', 'and, or and not', 'python-4', None),
    ('index', 'positions such as values[0]', 'python-5', None),
    ('slice', 'slices such as values[1:3]', 'python-5', None),
    ('len', 'len', 'python-5', None),
    ('for', 'for loops', 'python-6', None),
    ('range', 'range', 'python-6', None),
    ('augmented', '+= and -=', 'python-6', None),
    ('append', 'append', 'python-7', None),
    ('comprehension', 'list comprehensions', 'python-7', None),
    ('zip', 'zip', 'python-7', None),
    ('tuple', 'tuples and unpacking', 'python-8', None),
    ('default', 'default values', 'python-8', None),
    ('dict', 'dictionaries', 'python-9', None),
    ('in', 'in and not in', 'python-9', None),
    ('raise', 'raise ValueError', 'python-10', None),
    ('import', 'import', 'python-11', None),
    ('f-string', 'f-strings', 'python-11', None),
    ('conditional', 'x if test else y', None, PY_DOCS + 'reference/expressions.html#conditional-expressions'),
    ('chained', 'chained comparisons such as 0 <= x < 5', None, PY_DOCS + 'reference/expressions.html#comparisons'),
    ('while', 'while loops', None, PY_DOCS + 'reference/compound_stmts.html#the-while-statement'),
    ('break', 'break and continue', None, PY_DOCS + 'tutorial/controlflow.html#break-and-continue-statements'),
    ('enumerate', 'enumerate', None, PY_DOCS + 'library/functions.html#enumerate'),
    ('set', 'sets', None, PY_DOCS + 'tutorial/datastructures.html#sets'),
    ('sorted', 'sorted and sort', None, PY_DOCS + 'howto/sorting.html'),
    ('string-methods', 'string methods such as strip and lower', None, PY_DOCS + 'library/stdtypes.html#string-methods'),
    ('isinstance', 'isinstance and type', None, PY_DOCS + 'library/functions.html#isinstance'),
    ('keyword', 'keyword arguments such as f(x, size=2)', None, PY_DOCS + 'tutorial/controlflow.html#keyword-arguments'),
    ('lambda', 'lambda', None, PY_DOCS + 'tutorial/controlflow.html#lambda-expressions'),
    ('try', 'try and except', None, PY_DOCS + 'tutorial/errors.html#handling-exceptions'),
    ('with', 'with blocks', None, PY_DOCS + 'reference/compound_stmts.html#the-with-statement'),
    ('class', 'classes', None, PY_DOCS + 'tutorial/classes.html'),
    ('decorator', 'decorators such as @cuda.jit', None, PY_DOCS + 'glossary.html#term-decorator'),
    ('star', '*args and **kwargs', None, PY_DOCS + 'tutorial/controlflow.html#arbitrary-argument-lists'),
    ('yield', 'yield', None, PY_DOCS + 'tutorial/classes.html#generators'),
]

JAVASCRIPT = [
    ('js-let-const', 'let and const', 'web-0', None, r'\b(?:let|const)\b'),
    ('js-function', 'function', 'web-0', None, r'\bfunction\b'),
    ('js-arrow', 'arrow functions such as x => x * 2', 'web-0', None, r'=>'),
    ('js-strict', '=== and !==', 'web-0', None, r'===|!=='),
    ('js-object', 'objects such as {count: 1}', 'web-0', None, r'\{\s*[A-Za-z_$][\w$]*\s*:'),
    ('js-for-of', 'for...of loops', 'web-0', None, r'\bfor\s*\(\s*(?:const|let)\s+\w+\s+of\b'),
    ('js-map-filter', 'map and filter', 'web-0', None, r'\.(?:map|filter)\('),
    ('js-spread', 'spread syntax such as {...state}', 'web-1', None, r'\.\.\.'),
    ('js-ternary', 'test ? a : b', None, MDN + 'Operators/Conditional_operator', r'\s\?\s'),
    ('js-sort', 'sort', None, MDN + 'Global_Objects/Array/sort', r'\.sort\('),
    ('js-string-methods', 'string methods such as trim and includes', None,
     MDN + 'Global_Objects/String', r'\.(?:trim|toLowerCase|toUpperCase|includes|split)\('),
    ('js-try', 'try and catch', None, MDN + 'Statements/try...catch', r'\btry\s*\{'),
    ('js-json', 'JSON.parse and JSON.stringify', None, MDN + 'Global_Objects/JSON', r'\bJSON\.'),
    ('js-typeof', 'typeof', None, MDN + 'Operators/typeof', r'\btypeof\b'),
]

STRING_METHODS = {'strip', 'lower', 'upper', 'split', 'join', 'replace', 'startswith', 'endswith'}


def _call_name(node):
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return '.' + node.func.attr
    return ''


def python_constructs(code):
    """Ids from PYTHON for the constructs this code uses."""
    found = set()
    tree = ast.parse(code)
    # values[1, 0] indexes two dimensions; its tuple is not one the learner writes.
    index_tuples = {id(node.slice) for node in ast.walk(tree) if isinstance(node, ast.Subscript)}
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            found.add('power')
        elif isinstance(node, (ast.FunctionDef, ast.Return)):
            found.add('def')
            if isinstance(node, ast.FunctionDef):
                arguments = node.args
                if arguments.defaults or any(arguments.kw_defaults):
                    found.add('default')
                if arguments.vararg or arguments.kwarg:
                    found.add('star')
                if node.decorator_list:
                    found.add('decorator')
        elif isinstance(node, ast.If):
            found.add('if')
        elif isinstance(node, ast.BoolOp) or (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not)):
            found.add('logic')
        elif isinstance(node, ast.Subscript):
            found.add('slice' if isinstance(node.slice, ast.Slice) else 'index')
        elif isinstance(node, ast.For):
            found.add('for')
            if isinstance(node.target, ast.Tuple):
                found.add('tuple')
        elif isinstance(node, ast.AugAssign):
            found.add('augmented')
        elif isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp, ast.DictComp)):
            found.add('comprehension')
            if any(isinstance(g.target, ast.Tuple) for g in node.generators):
                found.add('tuple')
            if isinstance(node, ast.DictComp):
                found.add('dict')
            if isinstance(node, ast.SetComp):
                found.add('set')
        elif isinstance(node, ast.Tuple) and id(node) not in index_tuples:
            found.add('tuple')
        elif isinstance(node, ast.Dict):
            found.add('dict')
        elif isinstance(node, ast.Set):
            found.add('set')
        elif isinstance(node, ast.Compare):
            if any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops):
                found.add('in')
            if len(node.ops) > 1:
                found.add('chained')
        elif isinstance(node, ast.Raise):
            found.add('raise')
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            found.add('import')
        elif isinstance(node, ast.JoinedStr):
            found.add('f-string')
        elif isinstance(node, ast.IfExp):
            found.add('conditional')
        elif isinstance(node, ast.While):
            found.add('while')
        elif isinstance(node, (ast.Break, ast.Continue)):
            found.add('break')
        elif isinstance(node, ast.Lambda):
            found.add('lambda')
        elif isinstance(node, ast.Try):
            found.add('try')
        elif isinstance(node, ast.With):
            found.add('with')
        elif isinstance(node, ast.ClassDef):
            found.add('class')
        elif isinstance(node, (ast.Yield, ast.YieldFrom)):
            found.add('yield')
        elif isinstance(node, ast.Call):
            name = _call_name(node)
            if any(k.arg for k in node.keywords):
                found.add('keyword')
            if any(k.arg is None for k in node.keywords) or any(isinstance(a, ast.Starred) for a in node.args):
                found.add('star')
            found.update({'len': ['len'], 'range': ['range'], 'zip': ['zip'], 'enumerate': ['enumerate'],
                          '.append': ['append'], 'sorted': ['sorted'], '.sort': ['sorted'],
                          'set': ['set'], 'dict': ['dict'], '.get': ['dict'], '.items': ['dict'],
                          'isinstance': ['isinstance'], 'type': ['isinstance']}.get(name, []))
            if name[1:] in STRING_METHODS:
                found.add('string-methods')
    return found


def _javascript_code(code):
    """The code without string contents and comments, so that only syntax is matched."""
    code = re.sub(r'/\*.*?\*/|//[^\n]*', ' ', code, flags=re.S)
    return re.sub(r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`', '""', code)


def javascript_constructs(code):
    """Ids from JAVASCRIPT for the constructs this code uses."""
    plain = _javascript_code(code)
    return {item[0] for item in JAVASCRIPT if re.search(item[4], plain)}


def _number(lesson_id):
    return int(lesson_id.rsplit('-', 1)[1])


def lesson_uses(lesson):
    """[{id, label, lesson, url}] for one lesson, in teaching order.

    lesson is the id of the lesson that teaches the construct, and url the documentation
    when no lesson does. A construct taught by this lesson, or by a later lesson of the
    same path, is left out: the lesson itself introduces it.
    """
    if lesson.get('language') == 'javascript':
        table = [item[:4] for item in JAVASCRIPT]
        found = javascript_constructs(lesson['starter']) | javascript_constructs(lesson['solution'])
    else:
        table = PYTHON
        found = python_constructs(lesson['starter']) | python_constructs(lesson['solution'])
    uses = []
    for id, label, teacher, url in table:
        if id not in found:
            continue
        if teacher and teacher.rsplit('-', 1)[0] == lesson['course'] and _number(teacher) >= _number(lesson['id']):
            continue
        uses.append(dict(id=id, label=label, lesson=teacher, url=url))
    return uses
