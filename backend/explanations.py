"""One-line explanations of common errors, shown above the raw error in the lesson."""
import re

# The first matching pattern wins, so specific messages come before general ones.
EXPLANATIONS = {
    'python': [
        (r"SyntaxError: expected ':'",
         'Lines that start with def, if, elif, else, for or while end with a colon. Add one at the end of the line shown.'),
        (r"SyntaxError: .*(was never closed|unterminated|unmatched|does not match opening)",
         'A bracket or quote is not closed, or has no partner. Check the line shown and the line above it.'),
        (r'IndentationError: expected an indented block',
         'Lines inside a def, if or for block start with 4 more spaces than the line that opens the block.'),
        (r'(IndentationError|TabError)',
         'The spaces at the start of the line shown do not line up with the lines around it. Use 4 spaces for each level.'),
        (r'SyntaxError',
         'Python could not read this code. Look on the line shown, and the line above it, for a missing bracket, quote, colon or comma.'),
        (r'NameError: .*not defined',
         'Python does not know this name. It is often misspelled: check the spelling against where the name was first set.'),
        (r"(TypeError|AttributeError): .*'NoneType'",
         'A value is None. Often a function has no return statement, or still has the starter code’s return None.'),
        (r'TypeError: .*(positional arguments? but \d+ (were|was) given|missing \d+ required positional argument)',
         'The call and the def line have different numbers of inputs.'),
        (r'IndexError: .*out of range',
         'Positions start at 0, so the last item is at position len(items) - 1, also written [-1].'),
        (r'KeyError',
         'The dictionary has no such key. Check with key in d, or use d.get(key, default).'),
        (r'ZeroDivisionError',
         'Something was divided by zero. This often comes from len() of an empty list. Check for empty input first.'),
        (r'AttributeError: .*has no attribute',
         'This value has no attribute with that name. It may be None or a different type than you expect. Print type(value) to check.'),
    ],
    'javascript': [
        (r'ReferenceError: .*is not defined',
         'JavaScript does not know this name. Check its spelling, and define it with const, let or function before you use it.'),
        (r'TypeError: Cannot read properties of (undefined|null)',
         'The value before the dot is undefined or null. Check that the variable is set and that the function you called returns a value.'),
        (r'SyntaxError: Unexpected end of input',
         'A bracket, brace or quote is still open. Check that each one is closed.'),
        (r'SyntaxError: (Unexpected token|Unexpected identifier|Invalid or unexpected token|missing \) after)',
         'JavaScript could not read this code. Look on the line shown for a missing or extra bracket, brace, comma or quote.'),
    ],
}

# An error line such as "KeyError: 'a'", optionally after the runner's "Line 3: " prefix.
ERROR_LINE = re.compile(r'^(?:Line \d+: )?((?:\w+\.)*\w*(?:Error|Exception)\b.*)$', re.M)


def explain(text, language='python'):
    """Return the explanation for the last error line in text, or None."""
    found = ERROR_LINE.findall(text or '')
    if not found:
        return None
    return next((message for pattern, message in EXPLANATIONS.get(language, [])
                 if re.match(pattern, found[-1])), None)
