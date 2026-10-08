"""Python from zero: the Python that the other paths use, for people who have never coded."""
from textwrap import dedent

COURSES_PYTHON = [
    dict(id='python', title='Python from zero', subtitle='Variables, functions, lists, loops and errors',
         icon='code', color='green'),
]
LESSONS_PYTHON = []
TUTORIAL = 'https://docs.python.org/3/tutorial/'


def add(n, title, intro, concept, explanation, tasks, tip, hints, starter, solution, checks,
        diagram, reference, minutes=10, last=False):
    LESSONS_PYTHON.append(dict(
        id=f'python-{n}', course='python', title=title, minutes=minutes, xp=150 if last else 100,
        intro=intro, concept=concept, explanation=explanation, tasks=tasks, tip=tip, hints=hints,
        starter=dedent(starter).strip() + '\n', solution=dedent(solution).strip() + '\n',
        checks=[dict(label=a, expr=b) for a, b in checks], diagram=diagram, language='python',
        reference=dict(title=reference[0], url=reference[1])))


add(1, 'Store and print values',
    ('A program is a list of instructions. Python runs them in order, from the top line to the '
     'bottom line.\n\nprint shows a value as output: the text that appears when the program runs.'),
    'name = value\nprint(name)',
    ('items = 3 stores the number 3 under the name items. A name that holds a value is called a '
     'variable. The = sign means "store this value under this name". It does not ask whether two '
     'things are equal. Later lines can use the name. With price = 2 and delivery = 1 stored as '
     'well, total = items * price + delivery works out 3 * 2 + 1 = 7 and stores 7 in total. In '
     'Python, * means multiply. print(total) then shows the value inside its round brackets, 7. '
     'Storing a new value in a variable replaces the old one. A line that starts with # is a comment. Python skips it; it is a note for people '
     'who read the code.'),
    ['Change price to 2 and delivery to 1.',
     'Set total to items * price + delivery.',
     'Keep print(total) as the last line. Run the code: the output should be 7.'],
    'Run the starter before you change it. It prints 0, because total is still 0.',
    ['Each line with = stores the value on its right under the name on its left.',
     'For example, cups = 4 followed by cost = cups * 3 + 2 stores 14 in cost.',
     'Write price = 2, delivery = 1 and total = items * price + delivery, each on its own line.'],
    '''
    # Python runs these lines from top to bottom.
    items = 3
    price = 0
    delivery = 0
    # Change the next line to work out items * price + delivery.
    total = 0
    print(total)
    ''',
    '''
    items = 3
    price = 2
    delivery = 1
    total = items * price + delivery
    print(total)
    ''',
    [('price is 2', 'price == 2'),
     ('delivery is 1', 'delivery == 1'),
     ('total is 7', 'total == 7'),
     ('items is still 3', 'items == 3'),
     ('The last line printed is 7', 'last_printed() == "7"')],
    ['Store values', 'Work out total', 'Print total'],
    ('Python tutorial: an informal introduction', TUTORIAL + 'introduction.html'), minutes=8)

add(2, 'Write maths the Python way',
    ('Python can do any calculation a calculator can. Some symbols differ from the ones on paper, '
     'and when one line does several calculations, Python works them out in a fixed order.'),
    '+ add   - subtract   * multiply   / divide   ** power',
    ('Python uses * for multiply and / for divide. ** raises a number to a power: 3 ** 2 is '
     '3 × 3 = 9, also called 3 squared. In one line, Python works out ** first, then * and /, '
     'then + and -. Round brackets ( ) come before all of them. So 5 - 2 ** 2 is 5 - 4 = 1, but '
     '(5 - 2) ** 2 is 3 ** 2 = 9. A whole number such as 9 is an int. A number with a decimal '
     'point, such as 2.5, is a float. / always gives a float, even when the result is whole: '
     '6 / 3 is 2.0.'),
    ['Set error to 5 minus 2, then squared. Use brackets and **.',
     'Set average to 1 plus 4, divided by 2.',
     'Set rate to the change in height, 9 - 3, divided by the number of days, 4 - 1.'],
    'Without brackets, 1 + 4 / 2 is 1 + 2.0 = 3.0, because / runs before +.',
    ['Put brackets around each part that must be worked out first.',
     'For example, (2 + 6) / 4 is 2.0, but 2 + 6 / 4 is 3.5.',
     'Write error = (5 - 2) ** 2, average = (1 + 4) / 2 and rate = (9 - 3) / (4 - 1).'],
    '''
    # Replace each 0 with a calculation.

    # A guess of 5 when the answer is 2: 5 minus 2, squared.
    error = 0

    # The average of 1 and 4.
    average = 0

    # Growth per day of a plant: 3 cm on day 1, 9 cm on day 4.
    rate = 0

    print(error)
    print(average)
    print(rate)
    ''',
    '''
    error = (5 - 2) ** 2
    average = (1 + 4) / 2
    rate = (9 - 3) / (4 - 1)

    print(error)
    print(average)
    print(rate)
    ''',
    [('error is 9', 'error == 9'),
     ('average is 2.5', 'average == 2.5'),
     ('rate is 2.0 cm per day', 'rate == 2'),
     ('average and rate are floats', 'isinstance(average, float) and isinstance(rate, float)')],
    ['Brackets', '** then * and /', '+ and -'],
    ('Python tutorial: using Python as a calculator', TUTORIAL + 'introduction.html#numbers'),
    minutes=8)

add(3, 'Functions: def and return',
    ('A function is a named calculation. You give it inputs, and it gives back one value. You '
     'write it once and can use it as often as you need.'),
    'def area(width, height):\n    return width * height',
    ('def starts a function definition. area is the function’s name, and width and height are '
     'its parameters: the names it uses for its inputs. The def line ends with a colon (:). The '
     'lines under it are indented: they start with 4 spaces. They are the function’s body, and '
     'they run only when the function is called. Writing area(3, 4) calls the function: it runs '
     'the body with width = 3 and height = 4. '
     'return sends a value back to the code that called the function, so print(area(3, 4)) '
     'shows 12. print inside a function only shows a value; the caller gets nothing back. A '
     'function that ends without returning a value gives None, a special value that means "no '
     'value".'),
    ['Keep the def line: area takes width and height.',
     'In the body, multiply width by height.',
     'Return the product. Do not print it.'],
    'Run the starter first. It prints None, because return None gives back no value.',
    ['The caller gets the value that follows return.',
     'For example, a function with def double(n): and the indented line return n * 2 gives '
     'back twice its input: double(4) is 8.',
     'Replace return None with return width * height.'],
    '''
    def area(width, height):
        # Return width times height.
        return None

    print(area(3, 4))
    ''',
    '''
    def area(width, height):
        return width * height

    print(area(3, 4))
    ''',
    [('3 by 4 is 12', 'area(3, 4) == 12'),
     ('Zero width gives zero', 'area(0, 5) == 0'),
     ('Works with decimals', 'area(2.5, 2) == 5.0'),
     ('Returns a value, not None', 'area(1, 1) is not None')],
    ['Inputs', 'Function body', 'Return value'],
    ('Python tutorial: defining functions', TUTORIAL + 'controlflow.html#defining-functions'))

add(4, 'Decide with if',
    ('A program often has to choose what to do. A comparison such as value < low is either True '
     'or False, and an if statement runs its lines only when the comparison is True.'),
    'if value < low:\n    return low\nelif value > high:\n    return high\nelse:\n    return value',
    ('A comparison gives one of two values, True or False, called booleans. < means less than, '
     '> greater than, <= less than or equal to, >= greater than or equal to, == equal to, and != '
     'not equal to. == has two equals signs; a single = stores a value. if value < low: runs '
     'the indented lines under it only when value < low is True. elif, short for "else if", is '
     'tested only when every test above it was False. The lines under else run when nothing '
     'above them ran. return ends the function at once, so no later line in it runs. To combine '
     'comparisons, use and (True only when both sides are True), or (True when at least one '
     'side is True) and not (which turns True into False and False into True). In this '
     'exercise, clamp keeps a value between low and high, the way a volume control stops at 0 '
     'and at 10.'),
    ['If value is less than low, return low.',
     'Otherwise, if value is greater than high, return high.',
     'Otherwise, return value unchanged.'],
    'Test both edges. clamp(10, 0, 10) should return 10, and clamp(0, 0, 10) should return 0.',
    ['Test the low side first, then the high side, and return value when neither test is True.',
     'For example, if n < 0: followed by the indented line return 0 turns every negative n '
     'into 0.',
     'Write if value < low: return low, then elif value > high: return high, then else: return '
     'value. Put each return on its own indented line.'],
    '''
    def clamp(value, low, high):
        # Return low if value is less than low,
        # high if value is greater than high,
        # and value itself otherwise.
        return None

    print(clamp(15, 0, 10))
    ''',
    '''
    def clamp(value, low, high):
        if value < low:
            return low
        elif value > high:
            return high
        else:
            return value

    print(clamp(15, 0, 10))
    ''',
    [('Keeps a value that is inside the range', 'clamp(5, 0, 10) == 5'),
     ('Raises a low value to low', 'clamp(-10, -5, 5) == -5'),
     ('Lowers a high value to high', 'clamp(20, -5, 5) == 5'),
     ('Keeps values on the edges', 'clamp(10, 0, 10) == 10 and clamp(0, 0, 10) == 0')],
    ['Compare', 'True or False', 'Run the matching lines'],
    ('Python tutorial: if statements', TUTORIAL + 'controlflow.html#if-statements'))

add(5, 'Lists, positions and slices',
    ('A list holds several values in order, such as the scores from four games. Each value has '
     'a numbered position, so you can ask for the first one, the last one, or several in a row.'),
    'values[0]   values[-1]   values[1:3]   len(values)',
    ('A list is written in square brackets, with commas between the values: [4, 5, 6]. Each '
     'value is an item. Each item has a position, also called an index, and positions start at '
     '0. values[0] is the first item and values[1] the second. Negative positions count from '
     'the end, so values[-1] is the last item and values[-2] the one before it. len, short for '
     'length, gives the number of items: len(values). values[1:3] is a slice: a new list from position 1 up to, but '
     'not including, position 3. Leave out a number to go to the edge: values[:2] is the first '
     'two items, values[1:] is everything after the first item, and values[1:-1] stops before '
     'the last item. A slice copies items into a new list and leaves the original list '
     'unchanged. [] is an empty list.'),
    ['In last(values), return the item at position -1. values always has at least one item.',
     'In middle(values), return a slice that starts at position 1 and stops before the last '
     'item.',
     'Leave values unchanged in both functions. Reading values[-1] and taking a slice do not '
     'change the list.'],
    'middle([1, 2]) has no items between the first and the last, so it returns [].',
    ['Use a negative position for the last item, and a slice for the middle.',
     'For example, numbers[-2] is the second-last item, and numbers[2:-1] starts at position 2 '
     'and stops before the last item.',
     'Return values[-1] from last and values[1:-1] from middle.'],
    '''
    def last(values):
        # Return the last item in values.
        return None

    def middle(values):
        # Return every item except the first and the last.
        return None

    print(last([4, 5, 6]))
    print(middle([1, 2, 3, 4]))
    ''',
    '''
    def last(values):
        return values[-1]

    def middle(values):
        return values[1:-1]

    print(last([4, 5, 6]))
    print(middle([1, 2, 3, 4]))
    ''',
    [('Returns the last item', 'last([4, 5, 6]) == 6'),
     ('Works for a list with one item', 'last([9]) == 9'),
     ('Drops the first and the last item', 'middle([1, 2, 3, 4]) == [2, 3]'),
     ('Two items leave an empty list', 'middle([1, 2]) == []'),
     ('Both functions leave the input list unchanged',
      '(lambda v: last(v) == 3 and middle(v) == [2] and v == [1, 2, 3])([1, 2, 3])')],
    ['List', 'Position or slice', 'Item or new list'],
    ('Python tutorial: lists', TUTORIAL + 'introduction.html#lists'))

add(6, 'Repeat with for',
    ('A loop repeats lines of code. A for loop runs the same lines once for each item in a '
     'list, so one short function works for a list of any length.'),
    'result = 0\nfor value in values:\n    result += value',
    ('for value in values: takes the items of values one at a time. On each pass, value names '
     'the current item and the indented lines under for, called the loop body, run. To add up a '
     'list, start a running total at 0 before the loop and add one item on each pass. '
     'result += value is short for result = result + value. When the loop has visited every '
     'item, Python goes on to the first line after the body. That is why return result is '
     'indented at the level of for, not inside the body. range(3) gives the numbers 0, 1 and 2, '
     'so for _ in range(3): repeats its body three times; _ is a name for a value the body does '
     'not use. A function can call another function: mean can return total(values) / '
     'len(values). Python already has sum(values), which adds up a list. This exercise builds '
     'the same thing, so that you can see how a loop works.'),
    ['In total(values), start result at 0.',
     'Loop over values and add each item to result. Return result after the loop. Do not use '
     'sum() in total.',
     'In mean(values), return total(values) divided by len(values). mean is only called with '
     'at least one item.'],
    'total([]) should be 0. The loop body never runs, so result keeps its starting value.',
    ['Each pass of the loop adds one item to result.',
     'For example, count = 0, then for n in [2, 3]: with count += n in the body, leaves count '
     'at 5.',
     'In total, write for value in values: and indent result += value under it. Keep return '
     'result at the same indent as for. In mean, return total(values) / len(values).'],
    '''
    def total(values):
        # Add up the items with a for loop. Do not use sum().
        result = 0
        return result

    def mean(values):
        # Return the total divided by the number of items.
        return None

    print(total([1, 2, 3]))
    print(mean([2, 4]))
    ''',
    '''
    def total(values):
        result = 0
        for value in values:
            result += value
        return result

    def mean(values):
        return total(values) / len(values)

    print(total([1, 2, 3]))
    print(mean([2, 4]))
    ''',
    [('Adds up 1, 2 and 3', 'total([1, 2, 3]) == 6'),
     ('An empty list adds up to 0', 'total([]) == 0'),
     ('total adds with a loop, not sum()', 'not calls("sum", lambda: total([1, 2, 3]))'),
     ('Mean divides by the number of items', 'mean([1, 2, 6]) == 3'),
     ('Mean of 1 and 2 is 1.5', 'mean([1, 2]) == 1.5')],
    ['Start at 0', 'Add each item', 'Return the total'],
    ('Python tutorial: for statements', TUTORIAL + 'controlflow.html#for-statements'))

add(7, 'Build a new list',
    ('Many calculations take one list and give back another, such as the error of each '
     'prediction. You can build the new list in a loop, or write the same thing on one line.'),
    '[p - t for p, t in zip(predictions, targets)]',
    ('To build a new list, start with an empty list and add to it inside a loop. '
     'result.append(x) adds x to the end of result. append is a method: a function that belongs '
     'to a value and is called with a dot after the value. Python has a one-line form for the '
     'same job, called a list comprehension: [x * 2 for x in values] makes a new list with '
     'x * 2 for each x in values. zip(a, b) pairs up two lists by position: the first item of a '
     'with the first item of b, then the second items, and so on. Here, predictions are a '
     'model’s guesses and targets are the correct answers. for p, t in '
     'zip(predictions, targets): gives two names on each pass, one item from each list. zip '
     'stops at the end of the shorter list.'),
    ['Pair each prediction with its target, using zip. If one list is longer, stop at the end '
     'of the shorter one, as zip does.',
     'Work out p - t for each pair, in order.',
     'Return the new list of differences.'],
    'differences([], []) should be []. With nothing to pair, the new list stays empty.',
    ['Build the result with append in a loop, or with a list comprehension.',
     'For example, [a * b for a, b in zip([1, 2], [3, 4])] gives [3, 8].',
     'Return [p - t for p, t in zip(predictions, targets)].'],
    '''
    def differences(predictions, targets):
        # Return a list of prediction - target per pair.
        return None

    print(differences([3, 5], [1, 5]))
    ''',
    '''
    def differences(predictions, targets):
        return [p - t for p, t in zip(predictions, targets)]

    print(differences([3, 5], [1, 5]))
    ''',
    [('3 - 1 and 5 - 5 give [2, 0]', 'differences([3, 5], [1, 5]) == [2, 0]'),
     ('Subtracts the target from the prediction, in order',
      'differences([1, 4], [3, 1]) == [-2, 3]'),
     ('Works with decimals', 'differences([1.5], [1]) == [0.5]'),
     ('Empty lists give an empty list', 'differences([], []) == []'),
     ('Stops at the end of the shorter list',
      '[differences([5, 2, 9], [1, 2]), differences([1], [1, 2])] == [[4, 0], [0]]')],
    ['Two lists', 'zip pairs', 'New list'],
    ('Python tutorial: list comprehensions', TUTORIAL + 'datastructures.html#list-comprehensions'))

add(8, 'Return several values',
    ('Sometimes one result is not enough. A function might need to give back the smallest and '
     'the largest number, or the two parts of a list. Python groups such values in a tuple.'),
    'return low, high\nlow, high = low_high(values)',
    ('A tuple holds a fixed group of values in round brackets: (1, 3). return a, b gives back '
     'one tuple that holds both values. The caller can unpack it into separate names: '
     'low, high = low_high([3, 1, 2]) stores 1 in low and 3 in high. print(low, high) shows '
     'both values with a space between them. A tuple is not a list, so (1, 3) == [1, 3] is '
     'False. min(values) and max(values) give the smallest and the largest item. In '
     'def split_at(values, fraction=0.5):, the parameter fraction has a default value. A call '
     'that leaves it out, such as split_at(values), uses 0.5. fraction is the share of the items '
     'that go into the first part: 0.5 is half and 0.6 is 60%. int(2.7) turns a decimal number '
     'into a whole number by dropping the part after the decimal point, so it gives 2.'),
    ['In low_high(values), return min(values) and max(values) as a tuple. values always has at '
     'least one item.',
     'In split_at, find the cut position: int(len(values) * fraction).',
     'Return two lists: the items before the cut, and the items from the cut onwards. Leave '
     'values unchanged in both functions: min, max and slices read the list without changing '
     'it.'],
    'For five items and fraction 0.6, the cut is int(5 * 0.6) = 3, so the two parts have 3 and '
    '2 items.',
    ['Separate two returned values with a comma. Two slices, one before a position and one from '
     'it, split a list into two parts.',
     'For example, return n, n * 2 gives back a tuple such as (4, 8), and nums[:2], nums[2:] '
     'split nums at position 2.',
     'Return min(values), max(values). In split_at, set cut = int(len(values) * fraction), then '
     'return values[:cut], values[cut:].'],
    '''
    def low_high(values):
        # Return the smallest item, then the largest.
        return None

    def split_at(values, fraction=0.5):
        # Return the items before the cut, and the rest.
        return None

    print(low_high([3, 1, 2]))
    print(split_at([1, 2, 3, 4]))
    ''',
    '''
    def low_high(values):
        return min(values), max(values)

    def split_at(values, fraction=0.5):
        cut = int(len(values) * fraction)
        return values[:cut], values[cut:]

    low, high = low_high([3, 1, 2])
    print(low, high)
    print(split_at([1, 2, 3, 4]))
    ''',
    [('Smallest and largest of [3, 1, 2]', 'low_high([3, 1, 2]) == (1, 3)'),
     ('Both functions leave the input list unchanged',
      '(lambda v: low_high(v) == (1, 3) and split_at(v) == ([3], [1, 2]) and v == [3, 1, 2])'
      '([3, 1, 2])'),
     ('Splits in half by default', 'split_at([1, 2, 3, 4]) == ([1, 2], [3, 4])'),
     ('Splits at 60%', 'split_at([1, 2, 3, 4, 5], 0.6) == ([1, 2, 3], [4, 5])'),
     ('Rounds the cut down', 'split_at([1, 2, 3]) == ([1], [2, 3])')],
    ['Work out values', 'return a, b', 'Unpack'],
    ('Python tutorial: tuples', TUTORIAL + 'datastructures.html#tuples-and-sequences'),
    minutes=12)

add(9, 'Look things up with a dictionary',
    ('A dictionary stores values under names you choose, such as a count for each word. You '
     'look up a value by its name instead of by its position.'),
    'counts = {"red": 2, "blue": 1}\ncounts["red"]   counts.get("green", 0)',
    ('Text inside quotes, such as "red", is a string. A dictionary, or dict, stores pairs. In '
     'each pair, a key leads to a value: {"red": 2, "blue": 1} has the key "red" with the value '
     '2, and the key "blue" with the value 1. counts["red"] reads the value for the key "red". '
     'counts["red"] = 3 stores a new value; if the key is not in the dictionary yet, this adds '
     'it. Reading a key that is not there stops the program with a KeyError. To avoid that, '
     'test "red" in counts, which is True or False, or use counts.get("red", 0), which gives 0 '
     'when the key is missing. {} is an empty dictionary. Keys can also be numbers or tuples, '
     'such as ("idle", "start").'),
    ['Loop over words. The starter already creates the empty dictionary counts.',
     'For each word, add 1 to its count. A word seen for the first time starts from 0. Count '
     'words exactly as they are written: "Red" and "red" are different words.',
     'Return counts after the loop.'],
    'count_words([]) should return {}. The loop does not run, so the dictionary stays empty.',
    ['Use each word as a key and its count as the value.',
     'For example, after seen = {}, the line seen["x"] = seen.get("x", 0) + 1 sets seen["x"] '
     'to 1. Running the same line again sets it to 2.',
     'In the loop, write counts[word] = counts.get(word, 0) + 1. Return counts after the loop.'],
    '''
    def count_words(words):
        # Map each word to the number of times it appears.
        counts = {}
        return counts

    print(count_words(["red", "blue", "red"]))
    ''',
    '''
    def count_words(words):
        counts = {}
        for word in words:
            counts[word] = counts.get(word, 0) + 1
        return counts

    print(count_words(["red", "blue", "red"]))
    ''',
    [('Counts a repeated word', 'count_words(["a", "b", "a"]) == {"a": 2, "b": 1}'),
     ('One word appears once', 'count_words(["x"]) == {"x": 1}'),
     ('Counts a later word three times', 'count_words(["a", "b", "b", "b"]) == {"a": 1, "b": 3}'),
     ('No words give an empty dictionary', 'count_words([]) == {}'),
     ('"A" and "a" are different words', 'count_words(["A", "a", "a"]) == {"A": 1, "a": 2}')],
    ['Word', 'Look up its count', 'Add 1'],
    ('Python tutorial: dictionaries', TUTORIAL + 'datastructures.html#dictionaries'))

add(10, 'Read and raise errors',
    ('When Python cannot run a line, it stops and shows an error. The error tells you what went '
     'wrong and where. Your own functions can also stop with an error when their input makes no '
     'sense.'),
    'if not values:\n    raise ValueError("values is empty")',
    ('An error report is called a traceback. Read it from the bottom. The last line names the '
     'kind of error and gives a message, such as ZeroDivisionError: division by zero. The lines '
     'above it show where the error happened. Look for the lines that name exercise.py, which is '
     'your code: File "exercise.py", line 3, in safe_mean means line 3, inside safe_mean. Common kinds are NameError (a name that was never '
     'set, often a typo), TypeError (a value of the wrong kind, such as None where a number was '
     'expected), IndexError (a position past the end of a list) and KeyError (a missing '
     'dictionary key). raise ValueError("values is empty") stops the function at once and '
     'reports a ValueError with your message. Raise it as soon as you find bad input, so that '
     'the error names the real problem. An empty list counts as False in an if, so if not '
     'values: is True when values is [].'),
    ['Test whether values is empty.',
     'If it is, raise ValueError with a short message.',
     'Otherwise, return the mean of values.'],
    ('To see the error, add print(safe_mean([])) as the last line and run the starter. The last '
     'line of the traceback says ZeroDivisionError. Delete that line again before you check '
     'your answer.'),
    ['Test for an empty list before the division.',
     'For example, if n < 0: followed by the indented line raise ValueError("n is negative") '
     'rejects negative numbers.',
     'Add if not values: and, indented under it, raise ValueError("values is empty"). Keep the '
     'return line after it.'],
    '''
    def safe_mean(values):
        # Raise ValueError if values is empty.
        return sum(values) / len(values)

    print(safe_mean([2, 4]))
    ''',
    '''
    def safe_mean(values):
        if not values:
            raise ValueError("values is empty")
        return sum(values) / len(values)

    print(safe_mean([2, 4]))
    ''',
    [('Mean of 2 and 4 is 3', 'safe_mean([2, 4]) == 3'),
     ('One item is its own mean', 'safe_mean([5]) == 5'),
     ('Works with decimals', 'safe_mean([0.5, 1.5]) == 1.0'),
     ('Mean of 1 and 2 is 1.5', 'safe_mean([1, 2]) == 1.5'),
     ('Raises ValueError for an empty list', 'raises(ValueError, lambda: safe_mean([]))')],
    ['Check the input', 'Raise or continue', 'Return the mean'],
    ('Python tutorial: errors and exceptions', TUTORIAL + 'errors.html'))

add(11, 'Format text and import modules',
    ('Python comes with modules: files of ready-made functions, such as a square root. An '
     'f-string puts values into text, so a function can return a readable result.'),
    'import math\nmath.sqrt(16)   f"{name} = {value:.2f}"',
    ('A module is a file of Python code that other programs can use. import math loads the math '
     'module. After that, math.sqrt names its square root function, and math.sqrt(16) is 4.0. '
     'Put imports at the top of the program. Without the import, math.sqrt stops with '
     'NameError: name \'math\' is not defined. from math import sqrt loads one function, which '
     'you then call as sqrt(16). The other paths begin with lines such as import torch in the '
     'same way. An f-string is a string with f before the opening quote. Inside it, {name} is '
     'replaced by the value of name. Add :.2f after a value to show it rounded to exactly 2 '
     'decimal places: with value = 0.12345, f"{value:.2f}" is "0.12". In this exercise, a point '
     '(x, y) is a position on a graph, and its distance from the point (0, 0) is the square '
     'root of x ** 2 + y ** 2.'),
    ['Add import math as the first line.',
     'In distance(x, y), return the square root of x ** 2 + y ** 2.',
     'In describe(name, value), return an f-string such as "loss = 0.12", with value shown to 2 '
     'decimal places.'],
    ('describe("weight", 2) should return "weight = 2.00". :.2f always shows 2 decimal places, '
     'even for a whole number.'),
    ['Call a function from a module as module.function(...). Put the name and the value inside '
     'one f-string.',
     'For example, math.sqrt(25) is 5.0, and with n = 3, f"{n} items" is "3 items".',
     'Return math.sqrt(x ** 2 + y ** 2) from distance and f"{name} = {value:.2f}" from '
     'describe.'],
    '''
    # Add the import on the next line.


    def distance(x, y):
        # Return the square root of x ** 2 + y ** 2.
        return None

    def describe(name, value):
        # Return text such as "loss = 0.12".
        return None

    print(distance(3, 4))
    print(describe("loss", 0.12345))
    ''',
    '''
    import math


    def distance(x, y):
        return math.sqrt(x ** 2 + y ** 2)

    def describe(name, value):
        return f"{name} = {value:.2f}"

    print(distance(3, 4))
    print(describe("loss", 0.12345))
    ''',
    [('Distance to (3, 4) is 5.0', 'distance(3, 4) == 5.0'),
     ('Distance to (-3, 4) is 5.0, not negative', 'distance(-3, 4) == 5.0'),
     ('Takes the square root', 'abs(distance(1, 1) - 1.4142135) < 1e-6'),
     ('Shows 2 decimal places', 'describe("loss", 0.12345) == "loss = 0.12"'),
     ('Shows 2 decimal places for a whole number', 'describe("weight", 2) == "weight = 2.00"')],
    ['import math', 'Work out a value', 'Put it in text'],
    ('Python tutorial: modules', TUTORIAL + 'modules.html'))

add(12, 'Slope between two points',
    ('The slope of a line says how fast one value changes when another grows. Training a model '
     'uses the same idea: it measures how much the error changes when one of the model’s '
     'numbers changes.'),
    'slope = (y2 - y1) / (x2 - x1)',
    ('The slope of a straight line is how much y changes when x grows by 1. Between the points '
     '(x1, y1) and (x2, y2), it is the change in y divided by the change in x: (y2 - y1) / '
     '(x2 - x1). From (0, 1) to (1, 3), y rises by 2 while x grows by 1, so the slope is 2. A '
     'negative slope means that y falls as x grows. When x1 equals x2, the change in x is 0 and '
     'the division is impossible, so raise ValueError. A curve has a different slope at each '
     'point. Its slope at one point is called the derivative. To estimate it, take a second '
     'point very close to the first. For the curve y = (x − 3)², the slope between x = 0 and '
     'x = 0.001 is about −6. ML foundations lesson 3 calls this number the gradient.'),
    ['Raise ValueError when x1 equals x2.',
     'Work out the change in y, y2 - y1, and the change in x, x2 - x1.',
     'Return the change in y divided by the change in x.'],
    'Swapping the two points gives the same slope, because both changes flip their sign.',
    ['Test for equal x values first, then divide the two changes.',
     'For example, from (1, 2) to (3, 8), y changes by 6 and x by 2, so the slope is 6 / 2 = 3. To stop on bad input, put a test first: if n == 0: with raise ValueError("n must not be 0") under it.',
     'Add if x1 == x2: with raise ValueError("x1 and x2 must differ") under it, then return '
     '(y2 - y1) / (x2 - x1).'],
    '''
    def slope(x1, y1, x2, y2):
        # Raise ValueError if x1 equals x2. Otherwise
        # return the change in y / the change in x.
        return None

    print(slope(0, 1, 1, 3))
    ''',
    '''
    def slope(x1, y1, x2, y2):
        if x1 == x2:
            raise ValueError("x1 and x2 must differ")
        return (y2 - y1) / (x2 - x1)

    print(slope(0, 1, 1, 3))
    ''',
    [('From (0, 1) to (1, 3) the slope is 2', 'slope(0, 1, 1, 3) == 2'),
     ('A flat line has slope 0', 'slope(0, 1, 2, 1) == 0'),
     ('From (2, -3) back to (0, 0) the slope is -1.5', 'slope(2, -3, 0, 0) == -1.5'),
     ('Raises ValueError when x1 equals x2', 'raises(ValueError, lambda: slope(1, 0, 1, 5))'),
     ('Estimates the slope of (x - 3) ** 2 at x = 0 as -5.999, close to -6',
      'abs(slope(0, 9, 0.001, (0.001 - 3) ** 2) + 5.999) < 1e-9')],
    ['Two points', 'Change in y ÷ change in x', 'Slope'],
    ('Google ML Crash Course: gradient descent',
     'https://developers.google.com/machine-learning/crash-course/linear-regression/gradient-descent'),
    minutes=12)

add(13, 'Fix a broken function',
    ('A bug is a mistake that makes a program stop with an error or give a wrong result. The '
     'function in this exercise has three bugs. None of them stops the program, so you find '
     'them by comparing the output with the result you expect.'),
    'run → compare with the expected result → print values → fix one bug → run again',
    ('mse(a, b) should return the mean squared error of two lists of the same length: for each '
     'position i, square the difference a[i] − b[i], add up the squares, and divide by the '
     'number of items. For [2, 4] and [1, 6], the squares are 1 and 4, so the result is '
     '5 / 2 = 2.5. for i in range(len(a)): visits every position of a, and a[i] is the item '
     'at position i. To find a bug, run the '
     'code and compare what you see with what you expect. The check labels show which inputs '
     'give a wrong result. A print inside the loop, such as print(i, total), shows the values '
     'on each pass, so you can follow the function step by step. Delete those prints when you '
     'are done. When a bug stops the program instead, read the last line of the traceback and '
     'go to the line it names. For example, a def, if or for line without its colon gives '
     'SyntaxError: expected \':\'.'),
    ['Run the starter and compare its output with the expected 2.5.',
     'Add print(i, total) inside the loop to see each pass.',
     'Fix the three bugs, so that mse returns the mean squared error. a and b always have the '
     'same length, and at least one item.'],
    ('The starter prints two lines: a number printed inside mse, then None from the last line. '
     'A printed None often means that a function has no return.'),
    ['Look at the range, at the line that changes total, and at the last line of the function.',
     'range(len(a) - 1) misses the last position. total = replaces the total instead of adding '
     'to it. print shows a value but does not give it back.',
     'Use for i in range(len(a)):, then total += (a[i] - b[i]) ** 2, then return '
     'total / len(a).'],
    '''
    def mse(a, b):
        # Should return the mean of (a[i] - b[i]) ** 2
        # over every position i. It has three bugs.
        total = 0
        for i in range(len(a) - 1):
            total = (a[i] - b[i]) ** 2
        print(total / len(a))

    print(mse([2, 4], [1, 6]))
    ''',
    '''
    def mse(a, b):
        total = 0
        for i in range(len(a)):
            total += (a[i] - b[i]) ** 2
        return total / len(a)

    print(mse([2, 4], [1, 6]))
    ''',
    [('[2, 4] and [1, 6] give 2.5', 'mse([2, 4], [1, 6]) == 2.5'),
     ('Equal lists give 0', 'mse([1, 2], [1, 2]) == 0'),
     ('Uses the only item of a one-item list', 'mse([3], [1]) == 4'),
     ('Uses the last position too', 'mse([1, 2, 3], [1, 2, 0]) == 3')],
    ['Run', 'Compare and trace', 'Fix'],
    ('Python tutorial: errors and exceptions', TUTORIAL + 'errors.html#syntax-errors'),
    minutes=12, last=True)
