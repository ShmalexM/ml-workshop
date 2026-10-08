"""Original small examples and orientation, taught before the independent tasks."""
from textwrap import dedent

ORIENTATION = {'python': {'welcome': 'This path teaches the Python that the other paths use. It starts '
                       'with the first line of a program and needs no coding experience.',
            'goal': 'Write and fix the small functions, lists and loops that ML foundations '
                    'starts with.',
            'prerequisites': [],
            'terms': [['Program', 'A list of instructions that Python runs from top to bottom.'],
                      ['Variable', 'A name that holds a value, such as items = 3.'],
                      ['Output', 'What print shows when the program runs.']]},
 'foundations': {'welcome': 'Machine learning adjusts a function’s parameters using examples. '
                            'Begin with a line whose weight and bias you can inspect.',
                 'goal': 'Explain how a prediction changes, then learn its parameters from '
                         'data.',
                 'prerequisites': ['python'],
                 'terms': [['Model', 'A function that turns an input into a prediction.'],
                           ['Parameter',
                            'An adjustable number inside the model, such as weight or bias.'],
                           ['Training',
                            'Repeatedly changing parameters to reduce error on examples.']]},
 'pytorch': {'welcome': 'PyTorch stores numbers in tensors and records the operations needed '
                        'to calculate gradients. Use it to build the training loop from '
                        'Foundations.',
             'goal': 'Train a small model using automatic gradients and an optimizer.',
             'prerequisites': ['python', 'foundations'],
             'terms': [['Tensor', 'An array of numbers with a shape, data type, and device.'],
                       ['Gradient', 'How much a small parameter change affects the loss.'],
                       ['Autograd', 'PyTorch’s automatic gradient calculation.']]},
 'tensorflow': {'welcome': 'TensorFlow records gradients and provides Keras layers for '
                           'building models. This path uses the Foundations training loop. '
                           'PyTorch is optional. Matrix multiplication follows NumPy’s shape '
                           'rule: [batch, features] times [features, outputs] gives [batch, '
                           'outputs], so the inner sizes must match.',
                'goal': 'Train a Keras model and explain each training step.',
                'prerequisites': ['python', 'foundations'],
                'terms': [['Variable', 'A tensor whose value can be updated during training.'],
                          ['GradientTape',
                           'A context that records operations for differentiation.'],
                          ['Keras', 'A layer and training API used with TensorFlow here.']]},
 'modern': {'welcome': 'An AI app is a chain of steps. A tokenizer turns text into IDs, a '
                       'transformer produces vectors, and retrieval finds relevant text. '
                       'Everything runs locally without downloads or a model service. Prompt '
                       'and retrieval lessons do not generate answers.',
            'goal': 'Build and inspect the inputs and data used by an AI application.',
            'prerequisites': ['python', 'pytorch'],
            'terms': [['Token', 'A text piece represented by an integer ID.'],
                      ['Checkpoint', 'Saved model parameters learned during training.'],
                      ['Retrieval', 'Selecting relevant source material for a query.']]},
 'cuda': {'welcome': 'A GPU launches many threads, each assigned part of an array. This path '
                     'uses NumPy arrays and Numba’s CUDA API, so you need ML foundations and basic '
                     'NumPy first: creating an array, its shape and dtype, and indexing. Kernels '
                     'run in a CPU simulator. '
                     'GPU compilation, timing, and hardware race behavior require NVIDIA '
                     'hardware.',
          'goal': 'Write kernels with correct indices, bounds checks, and memory transfers.',
          'prerequisites': ['python', 'foundations'],
          'terms': [['Kernel', 'A function run by every thread in a launch.'],
                    ['Block', 'A group of threads that can cooperate.'],
                    ['Global index', 'A thread’s position across the whole launch.']]},
 'harness': {'welcome': 'An agent harness is the software that runs a model’s proposed '
                        'actions. Here you build and test its rules with recorded data. No '
                        'language model or external tool runs.',
             'goal': 'Control which actions a run can take and check whether it succeeded.',
             'prerequisites': ['python'],
             'terms': [['State', 'A named phase of a run, such as running or waiting.'],
                       ['Tool call', 'A proposed tool name and its arguments.'],
                       ['Trace', 'A recorded sequence of what happened during a run.']]},
 'backend': {'welcome': 'A backend receives requests from a client and returns results. '
                        'Practice the functions that validate and track those requests using '
                        'in-memory data. A deployed service also needs storage, '
                        'authentication, and concurrency controls. The lessons assume basic '
                        'Python: functions, dictionaries, sets, isinstance and raise.',
             'goal': 'Handle invalid requests and retries without losing track of the result.',
             'prerequisites': ['python'],
             'terms': [['Validation', 'Checking input types and values before using them.'],
                       ['Idempotency',
                        'Repeated requests have the effect of a single accepted request.'],
                       ['Cursor', 'A stable position from which to continue a result list.']]},
 'web': {'welcome': 'UI state is the data that determines what an interface displays. Practice '
                    'changing it with small JavaScript functions. The exercises run in '
                    'Node.js. Projects show how the functions fit into a browser app.',
         'goal': 'Keep the displayed state correct when requests or saved data change.',
         'prerequisites': [],
         'terms': [['State', 'The data that determines what the UI displays.'],
                   ['Reducer',
                    'A function that maps previous state and an action to next state.'],
                   ['Immutable update',
                    'Creating a changed copy instead of modifying the original.']]},
 'rl': {'welcome': 'In reinforcement learning, an agent chooses actions and learns from '
                   'rewards. Follow one episode through its steps, then calculate what those '
                   'rewards teach. These exercises use a small corridor and action-value '
                   'lists. They do not train a game agent.',
        'goal': 'Explain how rewards and ending signals affect an action-value update.',
        'prerequisites': ['python', 'foundations'],
        'terms': [['Observation', 'The information an environment gives the agent.'],
                  ['Reward', 'A numerical feedback signal after an action.'],
                  ['Episode',
                   'A sequence of actions and rewards ending at a goal or cutoff.']]},
 'data': {'welcome': 'Data can arrive twice, arrive out of order, or be too large to search as '
                     'one piece. Start with small inputs whose expected results you can work '
                     'out by hand.',
          'goal': 'Prepare text for retrieval and measure how many relevant results it finds.',
          'prerequisites': ['python'],
          'terms': [['Revision', 'A source-defined version of a record.'],
                    ['Chunk', 'A bounded piece of a larger document.'],
                    ['Recall',
                     'The fraction of expected relevant items that were retrieved.']]},
 'reliability': {'welcome': 'Before you run a service, decide what should happen when its '
                            'work fails. These exercises calculate retry schedules, redact log '
                            'fields, and check measurements. They do not call services or '
                            'deploy changes. Redacting by key name does not find secrets '
                            'written inside free text.',
                 'goal': 'Use failure cases and measurements to decide when to retry or '
                         'release.',
                 'prerequisites': ['python', 'backend'],
                 'terms': [['Retry budget',
                            'A limit on how long or how often an operation may retry.'],
                           ['Desired state',
                            'The configuration a system is intended to reach.'],
                           ['Percentile',
                            'A value below which a specified proportion of measurements '
                            'fall.']]},
 'interactive': {'welcome': 'Interactive apps combine state changes with elapsed time and '
                            'geometry. Practice those calculations as functions, then use the '
                            'project steps to find them in an app. The exercises are plain '
                            'functions and do not open windows or devices.',
                 'goal': 'Keep app state and motion predictable across pauses and repeated '
                         'events.',
                 'prerequisites': ['python'],
                 'terms': [['Lifecycle',
                            'The states an app moves through, such as active, paused, and '
                            'stopped.'],
                           ['Delta time', 'Elapsed time since the previous update.'],
                           ['Aspect ratio',
                            'Width divided by height; keeping it fixed avoids stretching.']]}}
GUIDES={}
def add(id,code,output,steps,question,choices,answer,feedback):
 GUIDES[id]=dict(code=dedent(code).strip()+'\n',output=output,steps=steps,question=question,choices=choices,answer=answer,feedback=feedback)

add('python-1','''
# Two cups at 3 each, plus a tip of 2.
cups = 2
cost = 3
tip = 2
bill = cups * cost + tip
print(bill)
''','8',['Python runs the lines in order. It stores 2 in cups, 3 in cost and 2 in tip.',
 'Then it works out 2 * 3 + 2 = 8, stores 8 in bill, and print shows it.'],'If cups = 2 becomes cups = 5, what is printed?',['8', '15', '17'],2,'Python works out 5 * 3 + 2 = 17. bill uses the value that cups has when that line runs.')
add('python-2','''
print(2 + 3 * 4)
print((2 + 3) * 4)
print(3 ** 2)
print(7 / 2)
''','14\n20\n9\n3.5',['* runs before +, so 2 + 3 * 4 is 2 + 12 = 14. Brackets make 2 + 3 run first: 5 * 4 = 20.',
 '3 ** 2 is 3 × 3 = 9. / gives a float, so 7 / 2 is 3.5.'],'If the first line becomes print(10 - 4 / 2), what is the first number printed?',['3.0', '8.0', '8'],1,'/ runs before -, so Python works out 4 / 2 = 2.0 first. 10 - 2.0 is 8.0, a float, because / always gives a float.')
add('python-3','''
def double(n):
    return n * 2

print(double(4))
print(double(10))
''','8\n20',['double(4) runs the body with n = 4. return sends back 4 * 2 = 8, and print shows it.',
 'double(10) runs the same body again, this time with n = 10, and gives back 20.'],'If return n * 2 becomes return n * 3, what is the first line printed?',['12', '8', '30'],0,'double(4) now returns 4 * 3 = 12. The name of a function does not change what its body does.')
add('python-4','''
def bigger(a, b):
    if a > b:
        return a
    else:
        return b

print(5 > 3)
print(0 <= 5 and 5 <= 10)
print(bigger(2, 7))
''','True\nTrue\n7',['5 > 3 is True. 0 <= 5 and 5 <= 10 is also True, because both comparisons are True.',
 'bigger(2, 7) tests 2 > 7. That is False, so the lines under else run and return b, which is 7.'],'If the last line becomes print(bigger(4, 4)), what is the last line printed?',['True', 'None', '4'],2,'4 > 4 is False, because 4 is not greater than itself. The lines under else run and return b, which is 4.')
add('python-5','''
scores = [70, 85, 90, 65]
print(scores[0])
print(scores[-1])
print(scores[1:3])
print(len(scores))
''','70\n65\n[85, 90]\n4',['Positions start at 0, so scores[0] is 70. Position -1 counts from the end, so scores[-1] is 65.',
 'scores[1:3] starts at position 1 and stops before position 3: [85, 90]. len counts the items: 4.'],'If scores[1:3] becomes scores[0:2], what is the third line printed?',['[70, 85]', '[85, 90]', '[70, 85, 90]'],0,'scores[0:2] starts at position 0 and stops before position 2, so it holds the items at positions 0 and 1: 70 and 85.')
add('python-6','''
numbers = [6, 1, 5]
running = 0
for number in numbers:
    running += number
    print(running)
print(running / len(numbers))
''','6\n7\n12\n4.0',['running starts at 0. Each pass adds one number: 0 + 6 = 6, then 6 + 1 = 7, then 7 + 5 = 12. The indented print shows each step.',
 'The last print is not indented, so it runs once, after the loop: 12 / 3 = 4.0.'],'If numbers becomes [6, 1, 5, 8], what is the last line printed?',['4.0', '5.0', '20'],1,'The total is now 20 and the list has 4 items, so the mean is 20 / 4 = 5.0. len(numbers) follows the length of the list.')
add('python-7','''
prices = [2, 5, 3]
doubled = []
for price in prices:
    doubled.append(price * 2)
print(doubled)
print([price * 2 for price in prices])
print([a + b for a, b in zip([1, 2], [10, 20])])
''','[4, 10, 6]\n[4, 10, 6]\n[11, 22]',['The loop appends price * 2 to the empty list doubled, once for each price.',
 'The list comprehension builds the same list in one line. zip pairs 1 with 10 and 2 with 20.'],'If price * 2 becomes price + 1 in both places, what is the first line printed?',['[3, 6, 4]', '[4, 10, 6]', '[2, 5, 3, 1]'],0,'Each price gets 1 added: 2 + 1, 5 + 1 and 3 + 1. The loop and the list comprehension both give [3, 6, 4].')
add('python-8','''
def first_last(values):
    return values[0], values[-1]

def scale(x, factor=2):
    return x * factor

first, last = first_last([7, 8, 9])
print(first, last)
print(first_last([7, 8, 9]))
print(scale(5), scale(5, 3))
''','7 9\n(7, 9)\n10 15',['first_last returns the tuple (7, 9). first, last = ... unpacks it into two names, and print shows both.',
 'scale(5) uses the default factor 2. scale(5, 3) passes 3, which replaces the default.'],'If factor=2 becomes factor=10, what is the last line printed?',['10 15', '50 15', '50 30'],1,'scale(5) now uses the default 10, so it gives 50. scale(5, 3) passes 3, which replaces the default, so it still gives 15.')
add('python-9','''
ages = {"ana": 31, "ben": 25}
print(ages["ana"])
ages["cy"] = 40
print("cy" in ages)
print(ages.get("dan", 0))
print(len(ages))
''','31\nTrue\n0\n3',['ages["ana"] looks up the key "ana" and gives its value, 31. ages["cy"] = 40 adds a new key.',
 '"cy" in ages is True. get gives 0, because "dan" is not a key; ages["dan"] would stop with a KeyError.'],'If ages.get("dan", 0) becomes ages.get("ben", 0), what is the third line printed?',['0', 'True', '25'],2,'"ben" is a key, so get returns its value, 25. The default 0 is used only when the key is missing.')
add('python-10','''
def safe_divide(a, b):
    if b == 0:
        raise ValueError("b must not be 0")
    return a / b

print(safe_divide(6, 3))
print(safe_divide(5, 2))
''','2.0\n2.5',['safe_divide(6, 3) tests 3 == 0. That is False, so raise does not run and the function returns 6 / 3 = 2.0.',
 'safe_divide(5, 0) would stop at raise. The last line of its traceback would read ValueError: b must not be 0.'],'If safe_divide(6, 3) becomes safe_divide(0, 3), what is the first line printed?',['0.0', 'ValueError: b must not be 0', '2.0'],0,'The test looks only at b, and b is 3. 0 / 3 is 0.0, so the function returns it without an error.')
add('python-11','''
import math

side = 9
root = math.sqrt(side)
print(root)
print(f"The square root of {side} is {root}")
print(f"{2 / 3:.3f}")
''','3.0\nThe square root of 9 is 3.0\n0.667',['import math loads the math module. math.sqrt is its square root function, and math.sqrt(9) is 3.0.',
 'In an f-string, {side} becomes 9 and {root} becomes 3.0. :.3f shows 2 / 3 with 3 decimal places: 0.667.'],'If :.3f becomes :.1f, what is the last line printed?',['0.667', '0.6', '0.7'],2,'2 / 3 is 0.6666…. Shown with 1 decimal place, it is rounded to 0.7.')
add('python-12','''
def loss(w):
    return (w - 3) ** 2

for step in [1, 0.1, 0.001]:
    print(round((loss(0 + step) - loss(0)) / step, 3))
''','-5.0\n-5.9\n-5.999',['loss(w) works out (w − 3)². ML calls a function that measures error a loss. Each pass prints the slope between w = 0 and w = step, rounded: round(number, 3) gives the number rounded to 3 decimal places, so round(-5.9994, 3) is -5.999.',
 'As step shrinks, the slope gets closer to −6, the derivative at w = 0. ML foundations lesson 3 calls it the gradient.'],'If loss(0 + step) - loss(0) becomes loss(3 + step) - loss(3), what is the last line printed?',['-5.999', '6.0', '0.001'],2,'At w = 3 the curve is at its lowest point, where it is flat. The slopes are 1.0, 0.1 and 0.001, shrinking towards 0.')
add('python-13','''
def count_above(values, limit):
    count = 0
    for value in values:
        print(value, value > limit)
        if value > limit:
            count += 1
    return count

print(count_above([3, 8, 5], 4))
''','3 False\n8 True\n5 True\n2',['The print inside the loop shows each value and whether it is above the limit.',
 'Two values are above 4, so count ends at 2. A print like this is a quick way to follow a loop.'],'If the call becomes count_above([3, 8, 5], 5), what is the last line printed?',['2', '1', '3'],1,'5 > 5 is False, so only 8 counts. The trace line for 5 now shows 5 False.')
add('foundations-1','''
# A small model: a starting amount plus a per-item amount.
items = 3
weight = 2
bias = 1
prediction = weight * items + bias
print(prediction)
''','7',['Start with 3 items. The weight says to add 2 for each item.','Multiply 2 × 3 to get 6, then add the starting amount 1.'], 'If items becomes 4, keeping the same weight and bias, what is the prediction?', ['9', '7', '12'],0,'2 × 4 + 1 = 9. The exercise puts this calculation in a function.')
add('foundations-2','''
predictions = [3, 5]
targets = [1, 5]
squared_errors = [(p - t) ** 2 for p, t in zip(predictions, targets)]
print(squared_errors)
print(sum(squared_errors) / len(squared_errors))
''','[4, 0]\n2.0',['Subtract each correct target from its prediction, then square the difference.','Average the squared errors: (4 + 0) / 2.'], 'If predictions becomes [3, 7], what mean squared error is printed?', ['4.0', '2.0', '8.0'],0,'Both errors are 2, so both squares are 4. Their mean is 4.')
add('foundations-3','''
weight = 0.0
target = 3.0
learning_rate = 0.1
gradient = 2 * (weight - target)
print(gradient)
print(round(weight - learning_rate * gradient, 2))
''','-6.0\n0.6',['For the loss (weight − target)², the slope is 2 × (weight − target).','Subtracting a negative slope increases the weight toward the target.'], 'If learning_rate becomes 0.5, what updated weight is printed?', ['3.0', '0.6', '-3.0'],0,'The gradient stays -6. The update is 0 - 0.5 × (-6) = 3.')
add('foundations-4','''
rows = list(range(10))
train = rows[:6]
validation = rows[6:8]
test = rows[8:]
print(len(train), len(validation), len(test))
''','6 2 2',['Use one partition to fit parameters and another to choose settings.','Keep the test partition for the final evaluation, after those choices.'], 'If rows becomes list(range(7)) and the slices stay the same, what is printed?', ['4 1 2', '6 1 0', '6 2 2'],1,('The fixed slices take rows 0 through 5, then row 6, then nothing. The exercise computes '
 'boundaries from the length.'))
add('foundations-5','''
train = [2.0, 4.0, 6.0]
mean = sum(train) / len(train)
variance = sum((x - mean)**2 for x in train) / len(train)
scale = variance ** 0.5
print(round((6.0 - mean) / scale, 3))
''','1.225',['Compute the training mean and population standard deviation.',
 'Subtract that mean and divide by that scale to standardize a value.'], 'If the 6.0 inside print(...) changes to 4.0, what is printed?', ['1.0', '0.0', '1.225'],1,'The training mean is 4. Subtracting it from 4 gives 0, whatever the nonzero scale.')
add('foundations-6','''
weight = 0.0
x, target, learning_rate = 1.0, 2.0, 0.1
for _ in range(3):
    prediction = weight * x
    error = prediction - target
    gradient = 2 * error * x
    weight -= learning_rate * gradient
    print(round(weight, 3))
''','0.4\n0.72\n0.976',['Predict with the current weight, then measure the difference from target 2.','Recompute the gradient after each update; the model has changed.'], 'If range(3) becomes range(2), what weights are printed?', ['0.4 then 0.72', '0.4 then 0.8', '0.72 then 0.976'],0,'The first update gives 0.4. The next error is -1.6, giving 0.4 + 0.32 = 0.72.')
add('pytorch-1','''
import torch
x = torch.tensor([[1., 2.], [3., 4.]])
weights = torch.tensor([[2.], [1.]])
print(list((x @ weights).shape))
print((x @ weights).tolist())
''','[2, 1]\n[[4.0], [10.0]]',['Each row has two features. Multiply them by weights 2 and 1, then add the products.',
 'Two rows produce two predictions, each with one value.'], 'If x has three rows and the same two columns, what shape does x @ weights have?', ['[2, 1]', '[3, 2]', '[3, 1]'],2,'The batch has three rows. The weight matrix gives each row one output.')
add('pytorch-2','''
import torch
x = torch.tensor(3., requires_grad=True)
y = x * x
y.backward()
print(x.grad.item())
''','6.0',['requires_grad asks PyTorch to record how this value is used.','backward computes the derivative of x², which is 2x at x = 3.'], 'If x starts at 4 instead of 3, what does x.grad.item() print?', ['16.0', '6.0', '8.0'],2,'The derivative of x² is 2x. At x = 4 it is 8.')
add('pytorch-3','''
import torch
layer = torch.nn.Linear(2, 1)
x = torch.zeros(3, 2)
print(list(layer(x).shape))
''','[3, 1]',['Linear(2, 1) maps two input features to one output for each example.','Three input rows produce three output rows.'], 'If layer becomes Linear(2, 4), what shape is printed?', ['[4, 3]', '[3, 4]', '[3, 2]'],1,'The batch still has three rows. Linear(2, 4) gives each row four outputs.')
add('pytorch-4','''
import torch
from torch.utils.data import DataLoader
loader = DataLoader(torch.arange(5), batch_size=2, shuffle=False)
print([batch.tolist() for batch in loader])
''','[[0, 1], [2, 3], [4]]',['The loader groups five values into batches of at most two.','The final batch can be smaller when drop_last is not enabled.'], 'If batch_size becomes 3, which batches are printed?', ['[[0, 1, 2], [3, 4, 0]]', '[[0, 1, 2], [3, 4]]', '[[0, 1, 2]]'],1,'The first batch has three items. The final batch keeps the two remaining items.')
add('pytorch-5','''
import torch
weight = torch.nn.Parameter(torch.tensor(0.))
optimizer = torch.optim.SGD([weight], lr=0.1)
optimizer.zero_grad()
loss = (weight - 2)**2
loss.backward()
optimizer.step()
print(round(weight.item(), 1))
''','0.4',['Clear old gradients, compute the current loss, then call backward.','step applies the gradient update to the parameter.'], 'If the optimizer learning rate becomes 0.2, what weight is printed?', ['0.4', '-0.8', '0.8'],2,'The gradient is -4. Subtracting 0.2 × (-4) from 0 gives 0.8.')
add('pytorch-6','''
import torch
model = torch.nn.Linear(1, 1, bias=False)
with torch.no_grad():
    model.weight.fill_(0)
optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
x, y = torch.tensor([[1.]]), torch.tensor([[2.]])
for _ in range(2):
    optimizer.zero_grad()
    loss = torch.nn.functional.mse_loss(model(x), y)
    loss.backward()
    optimizer.step()
model.eval()
with torch.no_grad():
    print(round(model(x).item(), 2))
''','0.72',['Each pass recomputes the loss using the updated weight.',
 'The weight moves from 0 to 0.4, then from 0.4 to 0.72.'], 'If range(2) becomes range(1), what prediction is printed?', ['0.4', '0.72', '2.0'],0,'One update moves the weight to 0.4. With input 1 and no bias, the prediction is also 0.4.')
add('tensorflow-1','''
import tensorflow as tf
x = tf.constant([[1., 2.], [3., 4.]])
weights = tf.constant([[2.], [1.]])
print(tf.matmul(x, weights).shape.as_list())
print(tf.matmul(x, weights).numpy().tolist())
''','[2, 1]\n[[4.0], [10.0]]',['Multiply each row’s two features by weights 2 and 1, then add the products.',
 'tf.matmul returns one prediction per row, so the result has shape [2, 1].'], 'If x has four rows and the same two columns, what shape does tf.matmul(x, weights) have?', ['[2, 4]', '[4, 1]', '[4, 2]'],1,'Four input rows give four predictions. The weights still have one output column.')
add('tensorflow-2','''
import tensorflow as tf
x = tf.Variable(3.)
with tf.GradientTape() as tape:
    y = x * x
print(tape.gradient(y, x).numpy().item())
''','6.0',['The tape records the multiplication while its context is active.','Ask for the derivative of y with respect to x after recording.'], 'If y becomes x * x + 3 * x, what gradient is printed at x = 3?', ['6.0', '18.0', '9.0'],2,'The derivative is 2x + 3, so it is 9 at x = 3.')
add('tensorflow-3','''
import tensorflow as tf
model = tf.keras.Sequential([tf.keras.Input(shape=(2,)), tf.keras.layers.Dense(1)])
print(model(tf.zeros((3, 2))).shape.as_list())
''','[3, 1]',['The Input shape describes features in one example, excluding batch size.','Dense(1) gives each input row one output.'], 'If Dense(1) becomes Dense(4), what shape is printed?', ['[4, 2]', '[3, 4]', '[3, 2]'],1,'Each of the three input rows now produces four outputs.')
add('tensorflow-4','''
import tensorflow as tf
dataset = tf.data.Dataset.from_tensor_slices([0, 1, 2, 3, 4]).batch(2)
print([batch.numpy().tolist() for batch in dataset])
''','[[0, 1], [2, 3], [4]]',['from_tensor_slices creates an element for each value.','batch groups those elements while keeping the final partial batch.'], 'What does batch(2, drop_remainder=True) give for the same data?', ['[[0, 1], [2, 3], [4]]', '[[0, 1], [2, 3]]', '[[0, 1], [2, 3], [4, 0]]'],1,'drop_remainder=True discards the final batch because it has only one item.')
add('tensorflow-5','''
import tensorflow as tf
weight = tf.Variable(0.)
optimizer = tf.keras.optimizers.SGD(0.1)
with tf.GradientTape() as tape:
    loss = (weight - 2)**2
gradient = tape.gradient(loss, weight)
optimizer.apply_gradients([(gradient, weight)])
print(round(float(weight.numpy()), 1))
''','0.4',['Record the loss, then differentiate it with respect to the trainable variable.','Pass each gradient together with the variable it updates.'], 'If SGD uses learning rate 0.2, what weight is printed?', ['0.4', '0.8', '-0.8'],1,'The gradient is -4. The updated weight is 0 - 0.2 × (-4) = 0.8.')
add('tensorflow-6','''
import tensorflow as tf
model = tf.keras.Sequential([
    tf.keras.Input(shape=(1,)),
    tf.keras.layers.Dense(1, use_bias=False, kernel_initializer="zeros"),
])
model.compile(optimizer=tf.keras.optimizers.SGD(0.1), loss="mse")
x, y = tf.constant([[1.]]), tf.constant([[2.]])
for _ in range(2):
    model.train_on_batch(x, y)
print(round(float(model(x).numpy()[0, 0]), 2))
''','0.72',['Each train_on_batch call computes the loss and applies one update.',
 'The weight goes from 0 to 0.4, then to 0.72, just as in the custom training step.'], 'If range(2) becomes range(1), what prediction is printed?', ['0.0', '0.72', '0.4'],2,'One update makes the weight 0.4. With input 1 and no bias, the prediction is 0.4.')
add('modern-1','''
vocabulary = {'[UNK]': 0, 'learn': 1, 'tensors': 2}
words = 'learn something'.split()
print([vocabulary.get(word, 0) for word in words])
''','[1, 0]',['Look up each word in the vocabulary.',
 'Use ID 0 for a word that is absent from the vocabulary.'], 'If the text becomes "tensors learn missing", what ID list is printed?', ['[2, 1, 0]', '[1, 2, 0]', '[2, 1, 3]'],0,'tensors maps to 2, learn to 1, and the missing word to the unknown ID 0.')
add('modern-2','''
batch_size, tokens, hidden_size = 2, 3, 8
attention_heads = 2
print([batch_size, tokens, hidden_size])
print(hidden_size // attention_heads)
''','[2, 3, 8]\n4',['There is one hidden vector per token, with shape [batch_size, tokens, hidden_size].',
 'Divide the hidden width evenly between the attention heads.'], 'If hidden_size becomes 12 with two attention heads, what is the second printed number?', ['6', '4', '24'],0,'Each head gets hidden_size / attention_heads = 12 / 2 = 6 values.')
add('modern-3','''
from langchain_core.prompts import ChatPromptTemplate
prompt = ChatPromptTemplate.from_messages([('human', 'Explain {topic}.')])
message = prompt.format_messages(topic='tensors')[0]
print(message.type)
print(message.content)
''','human\nExplain tensors.',['The template contains a named slot, topic.',
 'Formatting fills the slot and keeps the human role.'], 'If topic becomes "gradients", what content is printed?', ['Explain gradients.', 'Explain {topic}.', 'gradients'],0,'format_messages substitutes gradients into the {topic} slot.')
add('modern-4','''
from langchain_core.runnables import RunnableLambda
strip = RunnableLambda(lambda text: text.strip())
length = RunnableLambda(len)
pipeline = strip | length
print(pipeline.invoke('  hi  '))
''','2',['The first runnable removes surrounding spaces.','The second receives the first result, so it counts two characters.'], 'If the input becomes "  hello  ", what number is printed?', ['9', '2', '5'],2,'strip removes the four surrounding spaces. len then counts the five letters.')
add('modern-5','''
from llama_index.core.schema import TextNode
node = TextNode(
    text="A tensor has a shape.",
    metadata={"source": "notes", "index": 0},
    id_="notes:0",
)
print(node.text)
print(node.node_id)
print(node.metadata["source"])
''','A tensor has a shape.\nnotes:0\nnotes',['Keep the paragraph text, source, and index in one node.',
 'Set the ID explicitly so later results can identify the same paragraph.'], ('If metadata["source"] becomes "book" and id_ stays "notes:0", what are the last two '
 'printed lines?'), ['book:0 then book', 'notes:0 then book', 'notes:0 then notes'],1,('The ID and metadata are separate fields. Changing source metadata alone leaves the ID '
 'unchanged.'))
add('modern-6','''
query = set("tensor shape".split())
document_words = set("a tensor has a shape".split())
print(len(query & document_words))
''','2',['Convert each text to a set so a repeated word counts once.',
 'The intersection holds the words shared by the query and document.'], 'If the query becomes "tensor tensor loss", what score is printed?', ['2', '3', '1'],2,'The set contains tensor and loss. Only tensor is shared, so the score is 1.')
add('cuda-1','''
threads_per_block = 4
block_id = 2
thread_id = 1
global_id = block_id * threads_per_block + thread_id
print(global_id)
''','9',['Blocks and threads are numbered from zero. Two complete blocks contain eight threads.',
 'Add thread 1 to that offset to get index 9.'], 'What global ID does block 2, thread 3 have?', ['5', '12', '11'],2,'2 × 4 + 3 = 11. This is the same indexing rule used in a one-dimensional kernel.')
add('cuda-2','''
size, threads_per_block = 5, 4
blocks = (size + threads_per_block - 1) // threads_per_block
valid = [i for i in range(blocks * threads_per_block) if i < size]
print(blocks)
print(valid)
''','2\n[0, 1, 2, 3, 4]',['Round up the block count so all five elements have a thread.',
 'The launch has eight threads, and the guard keeps only indices 0 through 4.'], 'If size becomes 9, how many blocks are computed with four threads per block?', ['2', '3', '4'],1,'(9 + 4 - 1) // 4 is 3. Twelve threads cover nine elements, leaving three threads to skip.')
add('cuda-3','''
import numpy as np
from numba import cuda
host = np.array([1, 2], dtype=np.float32)
device = cuda.to_device(host)
device[0] = 9
print(host)
print(device.copy_to_host())
''','[1. 2.]\n[9. 2.]',['to_device copies the host values into separate storage.',
 'Changing that copy leaves host unchanged. copy_to_host reads the updated values.'], 'If device[0] = 9 becomes device[1] = 7, what does copy_to_host() print?', ['[7. 2.]', '[1. 2.]', '[1. 7.]'],2,'Only device index 1 changes. Copying back returns [1, 7].')
add('cuda-4','''
source = [[1, 2, 3], [4, 5, 6]]
out = [[0, 0] for _ in range(3)]
for row in range(2):
    for col in range(3):
        out[col][row] = source[row][col]
print(out)
''','[[1, 4], [2, 5], [3, 6]]',['The input has two rows and three columns. Allocate three output rows with two columns '
 'each.',
 'Swap row and column when writing each value.'], 'Where does 4, at source[1][0], land?', ['out[0][1]', 'out[1][0]', 'out[1][1]'],0,'The source coordinates (1, 0) become output coordinates (0, 1).')
add('cuda-5','''
import numpy as np
from numba import cuda, float32

@cuda.jit
def sum_pair(values, out):
    tid = cuda.threadIdx.x
    shared = cuda.shared.array(2, dtype=float32)
    shared[tid] = values[tid]
    cuda.syncthreads()
    if tid == 0:
        out[0] = shared[0] + shared[1]

values = cuda.to_device(np.array([2, 3], dtype=np.float32))
out = cuda.to_device(np.zeros(1, dtype=np.float32))
sum_pair[1, 2](values, out)
print(float(out.copy_to_host()[0]))
''','5.0',['Each of the two threads writes one shared slot, then waits at the barrier.',
 'Thread 0 reads both slots after the barrier and writes their sum.'], 'If values becomes [2, -3], what result is printed?', ['5.0', '2.0', '-1.0'],2,'Both signed values enter shared memory, so thread 0 adds 2 + (-3) = -1.')
add('cuda-6','''
a, scale, b = -3, 2, 1
value = scale * a + b
result = max(0, value)
print(value, result)
''','-5 0',['Compute scale × a + b, then clamp any negative result with ReLU.',
 'A kernel thread can do both steps before writing one output value.'], 'If a becomes 3, what pair is printed?', ['7 7', '6 6', '7 0'],0,'2 × 3 + 1 is 7. ReLU keeps it because it is positive.')

add('harness-1','''
state = "idle"
event = "start"
table = {("idle", "start"): "running"}
print(table.get((state, event), "invalid"))
''','running',['Treat state and event together as a lookup key.','The rule, rather than a model response, decides the next phase.'],'If event becomes "approve" while state stays "idle", what is printed?',['invalid', 'running', 'waiting'],0,('The table contains only idle/start. The missing pair uses the fallback "invalid". The '
 'exercise raises ValueError instead.'))
add('harness-2',"required = {'id'}\nproposed = {'id': 3, 'shell': 'extra'}\nprint(set(proposed) == required)",'False',['Convert argument keys to a set to ignore ordering.','Exact-key validation rejects the extra shell field.'],'If proposed becomes {"id": 3}, what comparison result is printed?',['False', '3', 'True'],2,'The proposed keys are exactly {"id"}, matching the required set.')
add('harness-3',"spent, next_cost, budget = 7, 3, 10\nprint(spent + next_cost <= budget)",'True',['Consider the cost of the proposed next step before running it.','Equality fits the budget; exceeding it does not.'],'If next_cost becomes 4, what is printed?',['True', '11', 'False'],2,'7 + 4 is 11, exceeding the budget of 10. The comparison returns False.')
add('harness-4','''
events = [
    {"kind": "tool", "name": "lookup", "ok": True},
    {"kind": "final", "answer": 7},
]
successful = {event["name"] for event in events
              if event["kind"] == "tool" and event["ok"] is True}
print(sorted(successful))
print(events[-1]["answer"])
''',"['lookup']\n7",['Collect names only from tool events with ok set to True.',
 'Read the final answer separately so it cannot hide a failed tool.'],'If the tool event’s ok becomes False, what is printed?',["['lookup'] then 7", '[] then False', '[] then 7'],2,'The failed event is excluded from successful. The recorded final answer stays 7.')
add('backend-1',"raw_title = '  Train a model  '\ntitle = raw_title.strip()\nprint(title)\nprint(bool(title))",'Train a model\nTrue',['Normalize harmless formatting first.','Check that a meaningful value remains after normalization.'],'If raw_title becomes three spaces, what is printed?',['A blank line, then True', 'A blank line, then False', 'None, then False'],1,('strip removes all three spaces. The empty string prints a blank line and bool("") is '
 'False.'))
add('backend-2','''
import copy
store = {"request-1": {"payload": {"x": 1}, "result": 42}}
key, payload = "request-1", {"x": 1}
if store[key]["payload"] == payload:
    print(copy.deepcopy(store[key]["result"]))
else:
    print("conflict")
''','42',['Look up the saved request by its key and compare payloads.',
 'Return the recorded result only for the same payload.'],'If payload becomes {"x": 2}, what is printed?',['42', '2', 'conflict'],2,'The same key already belongs to {"x": 1}. A different payload takes the conflict branch.')
add('backend-3','''
ids = [2, 7, 9, 12]
after = 7
remaining = [item_id for item_id in ids if item_id > after]
print(remaining[:1])
''','[9]',['A cursor names an ordering position rather than a page number.','Select IDs after that position, then apply the page size.'],'If after becomes 9, what is printed?',['[12]', '[9]', '[9, 12]'],0,'Only ID 12 is greater than 9. The one-item slice contains [12].')
add('backend-4',"required_health = [True, False]\nprint(all(required_health))",'False',['A process can be alive while a required dependency is unhealthy.','Readiness is false when any required dependency cannot serve work.'],'If required_health becomes [], what does all(required_health) print?',['True', 'False', 'It raises ValueError'],0,'all([]) is True: no required dependency is failing.')
add('web-1',"const before = {count: 1, label: 'runs'};\nconst after = {...before, count: before.count + 2};\nconsole.log(before.count, after.count);",'1 3',['Object spread creates a new object containing the previous fields.','Overriding count on the copy leaves the original count unchanged.'],'What is before.count after the update?',['3', '1', 'undefined'],1,'The original count stays 1. The exercise puts this update in a reducer function.')
add('web-2',"const currentRequest = 3;\nconst responseRequest = 2;\nconsole.log(currentRequest === responseRequest);",'false',['Each request receives an identity.','An old response must not replace the currently requested result.'],'If responseRequest becomes 3, what comparison result is printed?',['false', 'true', '3'],1,'Both IDs are 3, so strict equality returns true.')
add('web-3',"const source = ['GPU notes', 'API notes'];\nconst query = ' gpu '.trim().toLowerCase();\nconsole.log(JSON.stringify(source.filter(title => title.toLowerCase().includes(query))));",'["GPU notes"]',['Normalize both the query and the candidate text for a case-insensitive comparison.','filter returns a new array, leaving source intact.'],'If the query text becomes " notes ", what list is printed?',['["API notes"]', '["GPU notes","API notes"]', '["GPU notes"]'],1,'After trimming and lowercasing, notes appears in both titles.')
add('web-4',"const saved = JSON.parse('{\"version\":1,\"darkMode\":true}');\nconst theme = saved.darkMode ? 'dark' : 'light';\nconsole.log(theme);",'dark',['Parse stored text to recover data.','Translate the old boolean field into the new theme value.'],'If darkMode becomes false in the saved JSON, what theme is printed?',['dark', 'false', 'light'],2,'The false branch of the conditional chooses the string "light".')
add('rl-1',"position, action = 1, 1\nnext_position = max(0, min(4, position + action))\nprint(next_position)",'2',['Add the action to the current position.',
 'Clamp that result to the corridor’s range from 0 to 4.'],'What happens when position 0 receives action -1?',['Position becomes -1', 'Position stays 0', 'Position jumps to 4'],1,'The lower boundary is zero. The full environment also returns reward and ending signals.')
add('rl-2',"rewards = [1, 2]\ngamma = 0.5\nprint(rewards[0] + gamma * rewards[1])",'2.0',['Keep the immediate reward at full value.','Discount the next reward before adding it.'],'With gamma = 0, what is this return?',['2', '3', '1'],2,'A zero gamma leaves 1 + 0 × 2 = 1. Only the current reward contributes.')
add('rl-3','''
values = [1, 5, 2]
epsilon, draw, explore_index = 0.2, 0.1, 2
action = explore_index if draw < epsilon else values.index(max(values))
print(action)
''','2',['Compare the supplied draw with epsilon to decide whether to explore.',
 'Use the supplied exploration index or the index of the first largest value.'],'If draw becomes 0.8, which action index is printed?',['5', '2', '1'],2,'0.8 is above epsilon 0.2, so choose the index of value 5: index 1.')
add('rl-4',"reward, next_value, gamma = 1, 4, 0.5\nterminated = True\ntarget = reward if terminated else reward + gamma * next_value\nprint(target)",'1',['A terminated task has no future rewards to include in the target.',
 'For a continuing task, add the discounted estimate of the next value.'],'What target would a nonterminal truncated transition use here?',['1', '4', '3'],2,'Bootstrap the continuing task: 1 + 0.5 × 4 = 3. Truncation alone does not make the future value zero.')
add('data-1',"old = {'id': 'a', 'revision': 1}\nnew = {'id': 'a', 'revision': 3}\nchosen = new if new['revision'] > old['revision'] else old\nprint(chosen['revision'])",'3',['The same ID means these are two versions of one record.','Compare revisions to decide which version to retain.'],'If new["revision"] becomes 1, what revision is printed?',['3', '2', '1'],2,'The revisions tie. The strict greater-than comparison keeps old, whose revision is 1.')
add('data-2',"tokens = ['a', 'b', 'c', 'd', 'e']\nsize, overlap = 3, 1\nprint(tokens[:size])\nprint(tokens[size-overlap:size-overlap+size])","['a', 'b', 'c']\n['c', 'd', 'e']",['The first window starts at zero and contains three tokens.','Advance by size minus overlap: two positions, preserving c at the boundary.'],'If overlap becomes 0, what is the second printed list?',["['d', 'e']", "['c', 'd', 'e']", "['d', 'e', 'a']"],0,'The second start is size - overlap = 3. Only d and e remain.')
add('data-3',"graph = {'a': ['b'], 'b': ['a', 'c']}\nseen = {'a', 'b'}\nnext_nodes = set(graph['b']) - seen\nprint(sorted(next_nodes))","['c']",['A seen set records nodes already visited.','Subtracting it from neighbors prevents revisiting the cycle back to a.'],'If seen becomes {"a"}, what sorted next_nodes list is printed?',["['c']", "['a', 'c']", "['b', 'c']"],0,'The neighbors of b are a and c. Subtracting seen removes a and leaves c.')
add('data-4',"ranked = ['a', 'x', 'b']\nrelevant = {'a', 'b'}\nhits = set(ranked[:2]) & relevant\nprint(len(hits) / len(relevant))",'0.5',['Take the first two ranked positions, then count unique relevant hits.','One of two expected relevant documents is present.'],'What is recall at 3 for the same list?',['1.0', '0.5', '3.0'],0,'Both relevant IDs appear in the first three positions, so recall is 2 / 2 = 1.')
add('reliability-1',"base, cap = 2, 5\nprint([min(cap, base * 2**n) for n in range(4)])",'[2, 4, 5, 5]',['Double each candidate delay and limit it to cap.',
 'The exercise also checks whether the cumulative delay fits a budget.'],'If cap becomes 3, what four delays are printed?',['[2, 4, 8, 16]', '[2, 3, 3, 3]', '[2, 3, 4, 5]'],1,'The first delay is 2. Every later doubled value exceeds the cap, so each is limited to 3.')
add('reliability-2',"event = {'user': 'demo', 'token': 'example-only'}\nsafe = {key: '[REDACTED]' if key == 'token' else value for key, value in event.items()}\nprint(safe['token'])",'[REDACTED]',['Inspect the field name while creating a new dictionary.',
 'Replace the token value and keep the ordinary user value.'],'If the final print uses safe["user"], what is printed?',['[REDACTED]', 'demo', 'example-only'],1,'The user key is not redacted, so its value remains demo.')
add('reliability-3',"current = {'api': 'v1'}\ndesired = {'api': 'v2', 'worker': 'v1'}\nprint(sorted(set(desired) - set(current)))\nprint([key for key in current if key in desired and current[key] != desired[key]])","['worker']\n['api']",['Set differences identify services to create.',
 'Compare versions for shared names to identify updates.'],'If desired becomes {"api": "v1"}, what two lists are printed?',['[] then []', "['api'] then []", "[] then ['api']"],0,'Both mappings now have the same key and version, so there are no additions or updates.')
add('reliability-4',"import math\nlatencies = [10, 20, 30, 40]\nindex = math.ceil(0.95 * len(latencies)) - 1\nprint(sorted(latencies)[index])",'40',['Sort the measured latencies, then compute the nearest-rank index.',
 'For four samples, ceil(3.8) - 1 is 3, selecting the last value.'],'If 500 is appended to latencies, what p95 is printed?',['500', '40', '120'],0,'ceil(0.95 × 5) - 1 is index 4. The sorted value at that index is 500.')
add('interactive-1','''
state = "active"
event = "background"
table = {("active", "background"): "paused", ("paused", "resume"): "active"}
print(table.get((state, event), state))
''','paused',['Name the states and events in a transition table.',
 'Look up the pair, using the current state when the pair has no rule.'],'If state becomes "paused" and event becomes "resume", what is printed?',['paused', 'active', 'stopped'],1,'The paused/resume pair maps to active.')
add('interactive-2',"position, velocity = 10.0, 4.0\ndelta_time, max_delta = 0.5, 0.1\nprint(position + velocity * min(delta_time, max_delta))",'10.4',['Velocity is distance per unit time, so multiply it by elapsed time.','Cap an unusually long pause before applying movement.'],'If delta_time becomes 0.05, what position is printed?',['10.2', '10.4', '12.0'],0,'0.05 is below the 0.1 cap. The update is 10 + 4 × 0.05 = 10.2.')
add('interactive-3',"width, height = 800, 400\nbox_width, box_height = 300, 300\nscale = min(box_width / width, box_height / height)\nprint(width * scale, height * scale)",'300.0 150.0',['Compute how much each axis could be scaled to fit the box.','Use the smaller factor for both dimensions to preserve the aspect ratio.'],'If the box becomes 100 by 300, what displayed size is printed?', ['100.0 300.0', '100.0 50.0', '300.0 150.0'],1,'Width limits the scale to 100 / 800 = 0.125. The height becomes 400 × 0.125 = 50.')
add('interactive-4','''
events = [("a", 5), ("a", 5)]
merged = {}
for ident, points in events:
    merged.setdefault(ident, points)
print(sum(merged.values()))
''','5',['Read each (id, points) tuple and keep the first value for that ID.',
 'Sum the final mapping so repeated IDs contribute once.'],'If events becomes [("a", 5), ("a", 9), ("b", 2)], what total is printed?',['7', '16', '11'],0,'The first value for a is 5 and b contributes 2. The repeated a with 9 is ignored.')
