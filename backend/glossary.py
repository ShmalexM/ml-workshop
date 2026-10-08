"""Glossary: plain definitions of the terms the lessons use, and where each term first appears.

Each entry has an id, the term as shown, an optional sense that tells two meanings of
one word apart, a definition of one or two sentences, and the forms that link it in
lesson text. Forms match whole words, case-sensitively; a form that starts with a
lowercase letter also matches with a capital first letter. `paths` limits an entry to
some paths, so that a word such as "state" or "parameter" links the meaning each path
uses. `lesson` names the lesson that teaches the term.
"""
import re

PATH_IDS = ('python', 'foundations', 'pytorch', 'tensorflow', 'modern', 'cuda', 'harness',
            'backend', 'web', 'rl', 'data', 'reliability', 'interactive')
ML = ('foundations', 'pytorch', 'tensorflow', 'modern', 'cuda', 'rl')
NOT_ML = tuple(p for p in PATH_IDS if p not in ML)


def but(*paths):
    return tuple(p for p in PATH_IDS if p not in paths)


GLOSSARY = []


def term(id, name, definition, forms, paths=None, sense=None, lesson=None, exact=False):
    match = []
    for form in forms:
        match.append(form)
        if not exact and form[:1].islower():
            match.append(form[0].upper() + form[1:])
    GLOSSARY.append(dict(id=id, term=name, sense=sense, definition=definition, lesson=lesson,
                         paths=list(paths) if paths else None, match=match))


# Terms each path introduces in its first lesson.
term('program', 'Program', 'A list of instructions that Python runs from top to bottom.',
     ['program', 'programs'], lesson='python-1')
term('variable', 'Variable', 'A name that holds a value, such as items = 3.',
     ['variable', 'variables'], but('tensorflow'), sense='Python', lesson='python-1')
term('output', 'Output', 'What print shows when the program runs.', ['output'], ['python'],
     lesson='python-1')
term('model', 'Model', 'A function that turns an input into a prediction.', ['model', 'models'],
     lesson='foundations-1')
term('parameter-ml', 'Parameter', 'An adjustable number inside the model, such as weight or bias.',
     ['parameter', 'parameters'], ML, sense='machine learning', lesson='foundations-1')
term('training', 'Training', 'Repeatedly changing parameters to reduce error on examples.',
     ['training'], ML + ('python',), lesson='foundations-6')
term('tensor', 'Tensor', 'An array of numbers with a shape, data type, and device.',
     ['tensor', 'tensors'], lesson='pytorch-1')
term('gradient', 'Gradient', 'How much a small parameter change affects the loss.',
     ['gradient', 'gradients'], lesson='foundations-3')
term('autograd', 'Autograd', 'PyTorch’s automatic gradient calculation.',
     ['autograd', 'automatic differentiation'], lesson='pytorch-2')
term('tf-variable', 'Variable', 'A tensor whose value can be updated during training.',
     ['tf.Variable', 'variable', 'variables'], ['tensorflow'], sense='TensorFlow',
     lesson='tensorflow-1')
term('gradienttape', 'GradientTape', 'A context that records operations for differentiation.',
     ['GradientTape'], lesson='tensorflow-2')
term('keras', 'Keras', 'A layer and training API used with TensorFlow here.', ['Keras'],
     lesson='tensorflow-3')
term('token', 'Token', 'A text piece represented by an integer ID.', ['token', 'tokens'],
     lesson='modern-1')
term('checkpoint', 'Checkpoint', 'Saved model parameters learned during training.',
     ['checkpoint', 'checkpoints'])
term('retrieval', 'Retrieval', 'Selecting relevant source material for a query.', ['retrieval'],
     lesson='modern-6')
term('kernel', 'Kernel', 'A function run by every thread in a launch.', ['kernel', 'kernels'],
     ['cuda'], sense='CUDA', lesson='cuda-1')
term('block', 'Block', 'A group of threads that can cooperate.', ['block', 'blocks'], ['cuda'],
     sense='CUDA', lesson='cuda-1')
term('global-index', 'Global index', 'A thread’s position across the whole launch.',
     ['global index'], lesson='cuda-1')
term('state-run', 'State', 'A named phase of a run, such as running or waiting.',
     ['state', 'states'], ['harness'], sense='run', lesson='harness-1')
term('tool-call', 'Tool call', 'A proposed tool name and its arguments.',
     ['tool call', 'tool calls'], lesson='harness-2')
term('trace', 'Trace', 'A recorded sequence of what happened during a run.', ['trace', 'traces'],
     lesson='harness-4')
term('validation', 'Validation', 'Checking input types and values before using them.',
     ['validation', 'validate'], NOT_ML, sense='input', lesson='backend-1')
term('idempotency', 'Idempotency',
     'Repeated requests have the effect of a single accepted request.',
     ['idempotency', 'idempotency key', 'idempotent'], lesson='backend-2')
term('cursor', 'Cursor', 'A stable position from which to continue a result list.', ['cursor'],
     lesson='backend-3')
term('state-ui', 'State', 'The data that determines what the UI displays.', ['state'], ['web'],
     sense='UI', lesson='web-1')
term('reducer', 'Reducer', 'A function that maps previous state and an action to next state.',
     ['reducer', 'reducers'], lesson='web-1')
term('immutable-update', 'Immutable update',
     'Creating a changed copy instead of modifying the original.',
     ['immutable update', 'immutable updates'], lesson='web-1')
term('observation', 'Observation', 'The information an environment gives the agent.',
     ['observation', 'observations'], lesson='rl-1')
term('reward', 'Reward', 'A numerical feedback signal after an action.', ['reward', 'rewards'],
     ['rl'], lesson='rl-1')
term('episode', 'Episode', 'A sequence of actions and rewards ending at a goal or cutoff.',
     ['episode', 'episodes'], lesson='rl-2')
term('revision', 'Revision', 'A source-defined version of a record.', ['revision', 'revisions'],
     ['data'], lesson='data-1')
term('chunk', 'Chunk', 'A bounded piece of a larger document.', ['chunk', 'chunks'],
     lesson='data-2')
term('recall', 'Recall', 'The fraction of expected relevant items that were retrieved.',
     ['recall', 'recall at k'], lesson='data-4')
term('retry-budget', 'Retry budget', 'A limit on how long or how often an operation may retry.',
     ['retry budget'], lesson='reliability-1')
term('desired-state', 'Desired state', 'The configuration a system is intended to reach.',
     ['desired state'], lesson='reliability-3')
term('percentile', 'Percentile',
     'A value below which a specified proportion of measurements fall.',
     ['percentile', 'percentiles', 'p95'], lesson='reliability-4')
term('lifecycle', 'Lifecycle', 'The states an app moves through, such as active, paused, and stopped.',
     ['lifecycle'], lesson='interactive-1')
term('delta-time', 'Delta time', 'Elapsed time since the previous update.', ['delta time'],
     lesson='interactive-2')
term('aspect-ratio', 'Aspect ratio', 'Width divided by height; keeping it fixed avoids stretching.',
     ['aspect ratio'], lesson='interactive-3')

# Python.
term('function', 'Function',
     'A named piece of code that takes inputs and gives back a value. def creates one, and '
     'name(...) calls it.', ['function', 'functions'], lesson='python-3')
term('parameter', 'Parameter',
     'A name in a def line that receives an input when the function is called. In def '
     'area(width, height):, width and height are parameters.', ['parameter', 'parameters'],
     NOT_ML, sense='Python', lesson='python-3')
term('argument', 'Argument',
     'A value passed to a function when it is called. In area(3, 4), 3 and 4 are the arguments.',
     ['argument', 'arguments'], lesson='python-3')
term('return', 'return',
     'Ends a function and sends a value back to the code that called it. A function that ends '
     'without return gives None.', ['return', 'returns', 'returned'], but('rl'),
     lesson='python-3')
term('none', 'None', 'Python’s value for "no value". A function that ends without return gives None.',
     ['None'], lesson='python-3', exact=True)
term('integer', 'Integer', 'A whole number such as 3 or -2. Python calls the type int.',
     ['integer', 'integers', 'int'], lesson='python-2')
term('float', 'Float', 'A number with a decimal point, such as 2.5. / always gives a float.',
     ['float', 'floats'], lesson='python-2')
term('boolean', 'Boolean', 'One of the two values True and False. A comparison such as 3 > 2 gives a boolean.',
     ['boolean', 'booleans', 'bool'], lesson='python-4')
term('list', 'List',
     'Values kept in order inside square brackets, such as [4, 5, 6]. values[0] is the first '
     'item.', ['list'], lesson='python-5')
term('index', 'Index',
     'The position of an item, counted from 0. values[-1] counts from the end and gives the '
     'last item.', ['index', 'indices'], lesson='python-5')
term('slice', 'Slice',
     'Part of a list taken by position. values[1:3] is a new list from position 1 up to, but '
     'not including, position 3.', ['slice', 'slices', 'slicing'], lesson='python-5')
term('loop', 'Loop', 'Code that repeats. A for loop runs its body once for each item in a list.',
     ['loop', 'loops', 'for loop'], but('data'), lesson='python-6')
term('comprehension', 'List comprehension',
     'A one-line way to build a list: [x * 2 for x in values] holds x * 2 for each x in values.',
     ['list comprehension', 'comprehension', 'comprehensions'], lesson='python-7')
term('method', 'Method',
     'A function that belongs to a value and is called with a dot, such as values.append(4).',
     ['method', 'methods'], lesson='python-7')
term('tuple', 'Tuple',
     'A fixed group of values in round brackets, such as (1, 3). return a, b gives back a tuple.',
     ['tuple', 'tuples'], lesson='python-8')
term('string', 'String', 'Text inside quotes, such as "red".', ['string', 'strings'],
     lesson='python-9')
term('dictionary', 'Dictionary',
     'A dict stores values under keys, such as {"red": 2}. counts["red"] reads the value '
     'stored under "red".', ['dictionary', 'dictionaries', 'dict', 'dicts'], lesson='python-9')
term('key', 'Key', 'The name a dictionary stores a value under, such as "red" in {"red": 2}.',
     ['key', 'keys'], ['harness', 'backend', 'data', 'reliability', 'interactive'],
     lesson='python-9')
term('set', 'Set', 'A group of values with no order and no repeats, such as {"a", "b"}.',
     ['set'], ['harness', 'modern', 'data'])
term('traceback', 'Traceback',
     'The error report Python shows when a program stops. Its last line names the error.',
     ['traceback', 'tracebacks'], lesson='python-10')
term('exception', 'Exception',
     'An error that stops the program unless code catches it. raise creates one, and try and '
     'except catch one.', ['exception', 'exceptions'], lesson='python-10')
term('valueerror', 'ValueError',
     'The error to raise when an input has the right type but a value that makes no sense, '
     'such as an empty list.', ['ValueError'], lesson='python-10')
term('module', 'Module', 'A file of Python code that other programs can import, such as math or torch.',
     ['module', 'modules'], lesson='python-11')
term('import', 'import', 'Loads a module so that its functions can be used, as in import math.',
     ['import', 'imports'], lesson='python-11')
term('f-string', 'f-string', 'A string with f before the opening quote. {name} inside it is replaced by the value of name.',
     ['f-string', 'f-strings'], lesson='python-11', exact=True)
term('class', 'Class',
     'A template for making objects that share methods and attributes. Calling the class, as '
     'in Tokenizer(model), makes a new object.', ['class', 'classes'])
term('attribute', 'Attribute', 'A value stored on an object and read with a dot, such as tensor.shape.',
     ['attribute', 'attributes'])
term('lambda', 'lambda', 'A short function with no name: lambda x: x * 2 does what a def that returns x * 2 does.',
     ['lambda'], exact=True)
term('decorator', 'Decorator',
     'A line that starts with @ above a def. It hands the function to another function, as '
     '@cuda.jit does to make a GPU kernel.', ['decorator', 'decorators'])

# JavaScript.
term('javascript', 'JavaScript', 'The programming language that runs in web browsers. The Web app engineering lessons use it.',
     ['JavaScript'], lesson='web-0')
term('nodejs', 'Node.js', 'A program that runs JavaScript outside a browser. The Web exercises run in it.',
     ['Node.js'], lesson='web-0')
term('array', 'Array',
     'Values stored in order and read by position. A JavaScript array works like a Python '
     'list; a NumPy array holds numbers in a grid with a shape.', ['array', 'arrays'],
     lesson='web-0')
term('object', 'Object', 'Named fields in curly brackets, such as {name: "ana", score: 7}. A dot reads one field, as in result.name.',
     ['object', 'objects'], ['web'], sense='JavaScript', lesson='web-0')
term('arrow-function', 'Arrow function', 'A short JavaScript function: x => x * 2 takes x and returns x * 2.',
     ['arrow function', 'arrow functions'], lesson='web-0')
term('strict-equality', 'Strict equality', 'JavaScript’s === is true only when both the value and the type match, so 1 === "1" is false.',
     ['strict equality', '==='], lesson='web-0')
term('spread', 'Spread syntax', 'In JavaScript, {...state} copies the fields of state into a new object, and [...items] copies an array.',
     ['spread syntax', 'spread', 'spreading'], lesson='web-1')
term('pure-function', 'Pure function', 'A function whose result depends only on its inputs and that changes nothing outside itself.',
     ['pure function', 'pure functions'], lesson='web-1')
term('react', 'React', 'A JavaScript library for building user interfaces. It draws the page again when state changes.',
     ['React'])
term('json', 'JSON', 'A text format for data, such as {"version": 1}. JSON.parse turns the text into a value.',
     ['JSON'], lesson='web-4')

# Maths and machine learning.
term('slope', 'Slope', 'How much y changes when x grows by 1. Between two points it is (y2 − y1) / (x2 − x1).',
     ['slope', 'slopes'], lesson='python-12')
term('derivative', 'Derivative',
     'The slope of a curve at one point: how fast the output changes as the input grows. '
     'For (w − 3)², it is 2 × (w − 3).', ['derivative', 'derivatives'], lesson='python-12')
term('mean', 'Mean', 'The average: add the values and divide by how many there are. The mean of [2, 4] is 3.',
     ['mean'], ML + ('python',), lesson='python-6')
term('mse', 'Mean squared error (MSE)',
     'The mean of the squared differences between predictions and targets. Big misses count '
     'more than small ones.', ['mean squared error', 'MSE'], lesson='foundations-2')
term('loss', 'Loss',
     'One number that measures how wrong a model’s predictions are. Training changes the '
     'parameters to make it smaller.', ['loss', 'losses', 'loss function'],
     lesson='foundations-2')
term('gradient-descent', 'Gradient descent',
     'Training by repeated small steps against the gradient, so that the loss goes down.',
     ['gradient descent'], lesson='foundations-3')
term('learning-rate', 'Learning rate',
     'The size of each training step. An update subtracts learning rate × gradient from a '
     'parameter.', ['learning rate', 'learning rates'], lesson='foundations-3')
term('target', 'Target', 'The correct answer for an example. The loss compares each prediction with its target.',
     ['target', 'targets'], ['python', 'foundations', 'pytorch', 'tensorflow'], lesson='foundations-2')
term('label', 'Label', 'The correct answer stored with a training example; another word for target.',
     ['label', 'labels'], ['foundations', 'pytorch', 'tensorflow'], lesson='pytorch-4')
term('feature', 'Feature', 'One input value of an example, such as age or income.',
     ['feature', 'features'], ML, lesson='foundations-5')
term('standard-deviation', 'Standard deviation',
     'How far values usually are from their mean: the square root of the mean squared '
     'distance from the mean.', ['standard deviation'], lesson='foundations-5')
term('validation-data', 'Validation data',
     'Examples kept out of training and used to choose settings. Test data is kept for the '
     'final score.', ['validation data', 'validation set', 'validation'], ML,
     lesson='foundations-4')
term('inference', 'Inference', 'Using a trained model to make predictions on new inputs.',
     ['inference'], lesson='foundations-5')
term('epoch', 'Epoch', 'One pass over the whole training set.', ['epoch', 'epochs'],
     lesson='foundations-6')
term('batch', 'Batch',
     'A small group of examples handled together in one training step. Its size is usually '
     'the first number of a tensor’s shape.', ['batch', 'batches', 'minibatch'],
     ['foundations', 'pytorch', 'tensorflow'], lesson='pytorch-4')
term('shape', 'Shape',
     'The size of each dimension of a tensor or array. Three examples with two features each '
     'have shape (3, 2).', ['shape'], ML, lesson='pytorch-1')
term('dimension', 'Dimension',
     'One direction of a tensor or array. Shape (3, 2) has two dimensions: 3 rows and 2 '
     'columns.', ['dimension', 'dimensions'])
term('data-type', 'Data type',
     'The kind of number a tensor holds, such as a 32-bit float or a 64-bit integer. Also '
     'called dtype.', ['data type', 'dtype'], lesson='pytorch-1')
term('device', 'Device',
     'Where a tensor’s numbers are stored and computed: the CPU or a GPU. In CUDA the GPU is '
     'the device and the CPU is the host.', ['device'], ['pytorch', 'tensorflow', 'cuda'],
     lesson='cuda-3')
term('matrix', 'Matrix',
     'A grid of numbers in rows and columns. A matrix product multiplies each row by each '
     'column and adds up the products.', ['matrix', 'matrices', 'matrix multiplication'],
     lesson='pytorch-1')
term('vector', 'Vector', 'A list of numbers handled as one value, such as [-2, 1, 0, 3].',
     ['vector', 'vectors'])
term('broadcasting', 'Broadcasting',
     'Repeating a smaller tensor to match a bigger one, so that one bias is added to every '
     'row.', ['broadcasting', 'broadcasts'])
term('layer', 'Layer',
     'One step of a neural network. It turns input numbers into output numbers with its own '
     'weights.', ['layer', 'layers'], ML, lesson='pytorch-3')
term('neural-network', 'Neural network',
     'A model made of layers, with a function such as ReLU between them.',
     ['neural network', 'neural networks'], lesson='pytorch-3')
term('relu', 'ReLU', 'A function that replaces negative numbers with 0 and keeps positive ones.',
     ['ReLU'], lesson='pytorch-3')
term('optimizer', 'Optimizer', 'The object that updates parameters from their gradients, such as SGD.',
     ['optimizer', 'optimizers'], lesson='pytorch-5')
term('sgd', 'SGD',
     'Stochastic gradient descent: subtract learning rate × gradient from each parameter, '
     'using a batch of examples at a time.', ['SGD', 'stochastic gradient descent'],
     lesson='pytorch-5')
term('dataset', 'Dataset', 'A collection of examples used for training or evaluation.',
     ['dataset', 'datasets', 'training set', 'evaluation set'], lesson='pytorch-4')
term('embedding', 'Embedding',
     'A list of numbers that stands for a token or a piece of text. Similar meanings get '
     'similar numbers.', ['embedding', 'embeddings'])
term('transformer', 'Transformer',
     'The model design behind most language models. It updates each token’s vector using '
     'attention.', ['transformer', 'transformers'], lesson='modern-2')
term('attention', 'Attention',
     'The step in a transformer where each token’s vector takes in information from the '
     'other tokens.', ['attention'], ML, lesson='modern-2')
term('llm', 'Language model',
     'A model that reads tokens and predicts the next one. A large language model (LLM) is a '
     'big transformer trained on a lot of text.',
     ['large language model', 'language model', 'LLM'], lesson='modern-1')
term('tokenizer', 'Tokenizer', 'A tool that splits text into tokens and gives each token its ID.',
     ['tokenizer', 'tokenizers'], lesson='modern-1')
term('vocabulary', 'Vocabulary', 'The fixed list of tokens a tokenizer knows. Each one has an ID.',
     ['vocabulary'], lesson='modern-1')
term('prompt', 'Prompt', 'The text, or list of messages, sent to a language model as its input.',
     ['prompt', 'prompts'], lesson='modern-3')
term('metadata', 'Metadata', 'Data about data, such as the source name and position of a text chunk.',
     ['metadata'], lesson='modern-5')
term('query', 'Query', 'The text or request you search with.', ['query', 'queries'])
term('pipeline', 'Pipeline', 'A chain of steps in which each step’s output is the next step’s input.',
     ['pipeline', 'pipelines'])
term('numpy', 'NumPy', 'A Python library for arrays of numbers. PyTorch and TensorFlow follow its shape rules.',
     ['NumPy'])
term('gpu', 'GPU', 'A graphics processor: a chip that runs thousands of small calculations at the same time.',
     ['GPU', 'GPUs'], lesson='cuda-1')
term('cpu', 'CPU', 'The computer’s main processor. Each of its few cores runs one stream of instructions very fast.',
     ['CPU'], lesson='cuda-3')
term('thread', 'Thread', 'One worker in a GPU launch. Each thread runs the same kernel on its own index.',
     ['thread', 'threads'], ['cuda'], lesson='cuda-1')
term('host', 'Host', 'In CUDA, the CPU and its memory. The GPU is the device.', ['host'], ['cuda'],
     lesson='cuda-3')
term('shared-memory', 'Shared memory', 'Fast memory that all threads in one block can read and write.',
     ['shared memory'], lesson='cuda-5')
term('race', 'Race condition', 'A bug where the result depends on which thread runs first.',
     ['race condition', 'race'], ['cuda'], lesson='cuda-5')

# Engineering.
term('api', 'API', 'The functions or requests that a program offers to other programs.',
     ['API', 'APIs'], but('web'))
term('client', 'Client', 'The program that sends a request, such as a browser or an app.',
     ['client', 'clients'], lesson='backend-2')
term('server', 'Server', 'The program that receives requests and sends back responses.',
     ['server', 'servers'], lesson='backend-2')
term('request', 'Request', 'A message a client sends to ask a server for something, such as creating a task.',
     ['request', 'requests'], NOT_ML, lesson='backend-1')
term('response', 'Response', 'The message a server sends back for a request.',
     ['response', 'responses'], lesson='web-2')
term('database', 'Database', 'A program that stores data on disk and answers questions about it.',
     ['database', 'databases'])
term('service', 'Service', 'A program that keeps running and answers requests from other programs.',
     ['service', 'services'])
term('latency', 'Latency', 'The time between sending a request and getting its response, usually in milliseconds.',
     ['latency', 'latencies'], lesson='reliability-4')
term('exponential-backoff', 'Exponential backoff',
     'Waiting twice as long after each failed try, such as 1, 2, 4 and 8 seconds, up to a cap.',
     ['exponential backoff'], lesson='reliability-1')
term('telemetry', 'Telemetry', 'The logs, measurements and traces a running service sends out, so that people can see what it does.',
     ['telemetry'], lesson='reliability-2')
term('deployment', 'Deployment', 'Putting a version of a service into use, or the running copy that results.',
     ['deployment', 'deployments'], lesson='reliability-3')
term('agent', 'Agent',
     'A program that chooses actions. In reinforcement learning it learns from rewards; in an '
     'agent harness, a language model proposes the actions.', ['agent', 'agents'],
     ['rl', 'harness'], lesson='rl-1')
term('environment', 'Environment',
     'In reinforcement learning, the world the agent acts in. It takes an action and returns '
     'an observation and a reward.', ['environment'], ['rl'], lesson='rl-1')
term('policy', 'Policy', 'In reinforcement learning, the rule an agent uses to choose actions.',
     ['policy', 'policies'], ['rl'], lesson='rl-2')
term('return-rl', 'Return',
     'The rewards from one step to the end of an episode, added up with each later reward '
     'multiplied by gamma once more.', ['return', 'discounted return', 'discounted returns'],
     ['rl'], sense='reinforcement learning', lesson='rl-2')
term('discount', 'Discount factor (gamma)',
     'A number from 0 to 1 that shrinks future rewards: a reward k steps away counts gamma to '
     'the power k as much.', ['gamma', 'discount factor'], ['rl'], lesson='rl-2')
term('probability', 'Probability', 'How likely something is, from 0 (never) to 1 (always).',
     ['probability'])
term('graph', 'Graph', 'Nodes joined by links, such as pages that link to other pages.',
     ['graph', 'graphs'], ['data'], lesson='data-3')
term('node', 'Node', 'One item in a graph. LlamaIndex also calls a stored piece of text a node.',
     ['node', 'nodes'], ['data', 'modern'], lesson='data-3')
term('frame', 'Frame', 'One redraw of the screen. Most displays redraw 60 or more times a second.',
     ['frame', 'frames'], ['interactive'], lesson='interactive-2')

BY_TERM_ID = {entry['id']: entry for entry in GLOSSARY}

# Forms are matched as whole words: letters, digits, _ and - may not touch either end.
# Text in double quotes is data, such as a query or a title, so it is matched first and skipped.
_EDGE_BEFORE, _EDGE_AFTER = r'(?<![A-Za-z0-9_-])', r'(?![A-Za-z0-9_-])'
_QUOTED = '"[^"\\n]*"'


def entries_for(path):
    """The entries that link in lessons of this path."""
    return [entry for entry in GLOSSARY if entry['paths'] is None or path in entry['paths']]


def pattern(entries):
    """One regular expression for the forms of these entries, longest form first.

    src/glossary.ts builds the same expression, so the server and the browser link the
    same words.
    """
    forms = sorted({form for entry in entries for form in entry['match']}, key=len, reverse=True)
    return re.compile(_QUOTED + '|' + _EDGE_BEFORE + '(?:' + '|'.join(map(re.escape, forms)) + ')'
                      + _EDGE_AFTER)


def linked_terms(texts, path):
    """Ids of the entries that link in these texts, in order of first appearance."""
    entries = entries_for(path)
    owner = {form: entry['id'] for entry in entries for form in entry['match']}
    found = []
    expression = pattern(entries)
    for text in texts:
        for match in expression.finditer(text):
            if match.group() in owner and owner[match.group()] not in found:
                found.append(owner[match.group()])
    return found


def lesson_texts(lesson):
    """The texts in which terms link: the intro and explanation paragraphs."""
    return [*lesson['intro'].split('\n\n'), *lesson['explanation'].split('\n\n')]


def orientation_terms(*ids):
    """[term, definition] pairs for the Terms box on a path's first lesson."""
    return [[BY_TERM_ID[i]['term'], BY_TERM_ID[i]['definition']] for i in ids]
