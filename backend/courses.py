"""Original, offline curriculum and executable reference answers."""
from textwrap import dedent
from python_course import COURSES_PYTHON, LESSONS_PYTHON

# Python from zero comes first: it teaches the Python the other paths assume.
COURSES = [
    *COURSES_PYTHON,
    dict(id='foundations', title='ML foundations', subtitle='The ideas behind every framework', icon='book', color='green'),
    dict(id='pytorch', title='PyTorch', subtitle='Tensors, autograd and training loops', icon='flame', color='orange'),
    dict(id='tensorflow', title='TensorFlow', subtitle='The same ideas with TensorFlow & Keras', icon='box', color='blue'),
]
LESSONS = list(LESSONS_PYTHON)

def lesson(course, number, title, intro, concept, explanation, tasks, tip, hints, starter, solution, checks, diagram=None, minutes=12):
    refs = {'foundations': ('Google ML Crash Course', 'https://developers.google.com/machine-learning/crash-course/linear-regression'), 'pytorch': ('PyTorch: Learn the Basics', 'https://docs.pytorch.org/tutorials/beginner/basics/intro.html'), 'tensorflow': ('TensorFlow: automatic differentiation', 'https://www.tensorflow.org/guide/autodiff')}
    name,url=refs[course]
    LESSONS.append(dict(id=f'{course}-{number}', course=course, title=title, minutes=minutes, xp=150 if number==6 else 100, intro=intro, concept=concept, explanation=explanation, tasks=tasks, tip=tip, hints=hints, starter=dedent(starter).strip()+'\n', solution=dedent(solution).strip()+'\n', checks=[dict(label=a,expr=b) for a,b in checks], diagram=diagram or ['Data','Model','Prediction'], reference=dict(title=name,url=url)))

lesson('foundations',1,'Make a prediction',
'A model is a function with parameters you can learn from data. Start with the simplest one: a straight line.',
'prediction = weight × input + bias',
('Weight controls how much the output changes when the input increases by one. Bias shifts '
 'every prediction by the same amount. For x = 3, weight = 2 and bias = 1, the prediction '
 'is 7. Later, a training loop will learn the weight and bias from examples.'),
['Multiply the input by the weight.',
 'Add the bias to get the prediction.',
 'Return the number from predict(x, weight, bias).'],
'Try a zero weight. The result should equal the bias for any input.',
['Multiply the input by the weight first.','Add the bias to the product.','Return weight * x + bias.'],
'''
def predict(x, weight, bias):
    # Return the model's prediction
    return None

print(predict(3, 2, 1))
''',
'''
def predict(x, weight, bias):
    return weight * x + bias

print(predict(3, 2, 1))
''', [('Predicts 7 for x=3, w=2, b=1','predict(3,2,1)==7'),('Handles negative input','predict(-2,3,4)==-2'),('Bias remains when weight is zero','predict(100,0,5)==5'),('Works with fractional values','abs(predict(0.5,1.5,-0.25)-0.5)<1e-9')], ['Input x','Linear model','Prediction ŷ'],10)

lesson('foundations',2,'Measure the error',
'A prediction is only useful if you can tell how wrong it is. A loss function turns prediction errors into one number.\n\nMean squared error (MSE) squares each difference and averages the results. Big misses receive a larger penalty.',
'MSE = mean((prediction − target)²)',
('For predictions [2, 4] and targets [1, 6], the squared errors are [1, 4]. Their mean is '
 '(1 + 4) / 2 = 2.5. This loss measures how wrong the predictions are. The gradient in the '
 'next lesson tells you which way to change a weight.\n\n'
 'The code uses four pieces of Python. zip(predictions, targets) pairs the two lists by '
 'position. for p, t in ... unpacks each pair into two names. (p - t) ** 2 squares the '
 'difference. raise ValueError("...") stops the function when the input makes no sense, '
 'such as an empty list. Python from zero lessons 2, 7, 8 and 10 cover them.'),
['Pair each prediction with its target.',
 'Return the mean of their squared differences from mse(predictions, targets).',
 'Raise ValueError for empty lists or lists of different lengths.'],
'Check the lengths before using zip. Otherwise it silently stops at the shorter list.',
['Check that both lists are nonempty and have the same length before using zip.',
 'raise stops the function with an error. For example, if age < 0: raise ValueError("age '
 'must not be negative") rejects a negative age.',
 'For each pair from zip(predictions, targets), square p - t. Return sum((p - t) ** 2 for '
 'p, t in zip(predictions, targets)) / len(targets).'],
'''
def mse(predictions, targets):
    # Validate the inputs and compute the average squared error.
    return None

print(mse([2, 4], [1, 6]))
''',
'''
def mse(predictions, targets):
    if not predictions or len(predictions) != len(targets):
        raise ValueError('Expected nonempty, matching lists')
    return sum((p - t) ** 2 for p, t in zip(predictions, targets)) / len(targets)

print(mse([2, 4], [1, 6]))
''', [('MSE is 2.5', 'mse([2,4],[1,6])==2.5'),
 ('Errors of -2 and +2 count the same', 'mse([-2,2],[0,0])==4'),
 ('Empty lists rejected', 'raises(ValueError, lambda: mse([],[]))'),
 ('Mismatched lists rejected', 'raises(ValueError, lambda: mse([1],[1,2]))'),
 ('More predictions than targets rejected', 'raises(ValueError, lambda: mse([1,2],[1]))')], ['Predict','Compare','Average error'])

lesson('foundations',3,'Follow the gradient',
('The gradient tells you how the loss changes when you nudge a parameter. With one '
 'parameter, it is the derivative: the slope of the loss curve. Gradient descent moves the '
 'parameter a small step downhill.'),
'next_weight = weight − learning_rate × gradient',
('This toy model has no input; its prediction is the weight, so its loss is (weight − '
 'target)². At weight 0 and target 3, the gradient is 2 × (0 − 3) = −6. A learning rate of 0.1 gives the '
 'update 0 − 0.1 × (−6) = 0.6. Try the plot below to see how the learning rate changes '
 'each step.\n\n'
 'Where 2 × (weight − target) comes from: call the difference d = weight − target, so the '
 'loss is d × d. Raise the weight by a small amount h. The difference becomes d + h, and '
 'the loss becomes (d + h)² = d² + 2 × d × h + h². The loss grew by 2 × d × h + h². '
 'Divide that by h to get the slope: 2 × d + h. As h shrinks toward 0, the slope gets '
 'closer to 2 × d, which is 2 × (weight − target). Python from zero lesson 12 measured '
 'the same slope with h = 0.001 and got about −6.'),
['Compute the gradient of (weight − target)².',
 'Subtract learning_rate times the gradient from weight.',
 'Return the updated weight from step(weight, target, learning_rate).'],
'A positive gradient means loss rises as the weight rises. Step left.',
['The derivative is 2 * (weight - target).','Subtract learning_rate times that derivative.','Return weight - learning_rate * 2 * (weight - target).'],
'''
def step(weight, target, learning_rate):
    # Return the updated weight.
    return None

print(step(0, 3, 0.1))
''',
'''
def step(weight, target, learning_rate):
    return weight - learning_rate * 2 * (weight - target)

print(step(0, 3, 0.1))
''', [('Moves toward target','abs(step(0,3,.1)-.6)<1e-9'),('Moves down when above target','abs(step(5,3,.1)-4.6)<1e-9'),('Zero gradient leaves weight unchanged','step(3,3,.1)==3'),('Zero learning rate freezes training','step(1,3,0)==1')], ['Loss','Gradient','Update'])

lesson('foundations',4,'Train, validate, test',
('A model can fit its training examples and still fail on new data. Generalization means '
 'making useful predictions on examples it has never trained on. Use training data to fit '
 'weights, validation data to choose settings, and test data for a final evaluation.'),
'fit on train → choose with validation → report on test',
('For ten rows, the first six become training data, the next two validation data, and the '
 'last two test data. For rows in time order, train on earlier rows and test on later '
 'ones. Using future rows during training would give the model information it cannot have '
 'when making a prediction.'),
['Find the boundaries at 60% and 80% of the number of rows, rounded down.',
 'Keep the rows in their current order.',
 'Return the three lists from split_data(rows) as one tuple: return train, validation, '
 'test. Leave rows unchanged.'],
'For seven rows, the boundaries are 4 and 5. Check that all seven rows appear exactly once.',
['Use len(rows) to find the number of rows.',
 'Set train_end = int(len(rows) * 0.6) and val_end = int(len(rows) * 0.8).',
 'Return rows[:train_end], rows[train_end:val_end], rows[val_end:].'],
'''
def split_data(rows):
    # Return train, validation, test.
    return None

print(split_data(list(range(10))))
''',
'''
def split_data(rows):
    train_end = int(len(rows) * 0.6)
    val_end = int(len(rows) * 0.8)
    return rows[:train_end], rows[train_end:val_end], rows[val_end:]

print(split_data(list(range(10))))
''', [('60/20/20 for ten rows','split_data(list(range(10)))==(list(range(6)),[6,7],[8,9])'),('No dropped rows for odd size','sum((list(x) for x in split_data(list(range(7)))),[])==list(range(7))'),('Empty input stays empty','split_data([])==([],[],[])')], ['Training','Validation','Test'])

lesson('foundations',5,'Scale your features',
('A feature is one input value, such as age or income. When features use very different '
 'units, one learning rate may not suit every weight. Standardization subtracts the '
 'training mean, then divides by the training standard deviation.'),
'z = (x − training_mean) / training_std',
('Training values [1, 3] have mean 2 and population standard deviation 1. Subtracting 2 '
 'and dividing by 1 turns values [1, 3, 5] into [-1, 1, 3]. Reuse those training '
 'statistics for new predictions, also called inference. For constant training values, use '
 'scale 1 to avoid division by zero.'),
['Compute the mean and population standard deviation of train. Raise ValueError if train '
 'is empty.',
 'Use scale 1 when the standard deviation is zero.',
 'Return a list of transformed values from standardize(train, values).'],
'Try standardize([4, 4], [4, 5]). A scale of 1 gives [0, 1].',
['Compute the mean of train, not values. Variance is the mean squared distance from that '
 'mean; its square root is the scale.',
 'raise stops the function with an error. For example, if age < 0: raise ValueError("age '
 'must not be negative") rejects a negative age.',
 'If scale == 0, set scale = 1.0. Return [(x - mean) / scale for x in values].'],
'''
def standardize(train, values):
    # Return a list of standardized values.
    return None

print(standardize([1, 3], [1, 3, 5]))
''',
'''
def standardize(train, values):
    if not train:
        raise ValueError("Training data cannot be empty")
    mean = sum(train) / len(train)
    variance = sum((x - mean) ** 2 for x in train) / len(train)
    scale = variance ** 0.5
    if scale == 0:
        scale = 1.0
    return [(x - mean) / scale for x in values]

print(standardize([1, 3], [1, 3, 5]))
''', [('Uses training statistics', 'standardize([1,3],[1,3,5])==[-1,1,3]'),
 ('Handles constant feature', 'standardize([4,4],[4,5])==[0,1]'),
 ('Transforms empty evaluation set', 'standardize([1,2],[])==[]'),
 ('Rejects empty training data', 'raises(ValueError, lambda: standardize([], [1]))')], ['Fit statistics','Save statistics','Transform'])

lesson('foundations',6,'A complete training loop',
('You can now learn the weight and bias of a line from examples. Each pass predicts the '
 'outputs, computes both gradients, and updates the parameters. The training data here '
 'follows y = 2x + 1.'),
'error = weight × x + bias − y   dw = mean(2 × error × x)   db = mean(2 × error)',
('An epoch is one pass over the training set. With x = 1, y = 3, and both parameters at '
 'zero, the error is −3. Both gradients are −6, so learning rate 0.1 moves weight and bias '
 'to 0.6. Compute both gradients from the same old parameters so they describe the same '
 'predictions.\n\n'
 'Where dw and db come from: for one example, the loss is error², and lesson 3 showed '
 'that the slope of a square is 2 × error. Raising the bias by a small amount h raises the '
 'prediction, and so the error, by h. So the loss changes 2 × error times as fast as the '
 'bias: db = 2 × error. Raising the weight by h raises the prediction by h × x, because '
 'the weight is multiplied by x. So the loss changes 2 × error × x times as fast as the '
 'weight: dw = 2 × error × x. The loss of the training set is the mean over its examples, '
 'so each gradient is the mean of these values.'),
['Start weight and bias at zero in train(xs, ys, epochs=400, lr=0.05).',
 'For each epoch, compute all errors and both mean gradients before updating either '
 'parameter.',
 'Return the learned (weight, bias).'],
'Test one epoch on xs=[1], ys=[3], lr=0.1. Both parameters should become 0.6.',
['For each pair, error = weight * x + bias - y.',
 'Compute dw from 2 * error * x and db from 2 * error. Average each over all examples.',
 'After computing both gradients, set weight -= lr * dw and bias -= lr * db.'],
'''
def train(xs, ys, epochs=400, lr=0.05):
    weight, bias = 0.0, 0.0
    # Compute both gradients, then update weight and bias each epoch.
    return weight, bias

print(train([-2, -1, 0, 1, 2], [-3, -1, 1, 3, 5]))
''',
'''
def train(xs, ys, epochs=400, lr=0.05):
    weight, bias = 0.0, 0.0
    for _ in range(epochs):
        errors = [weight * x + bias - y for x, y in zip(xs, ys)]
        dw = sum(2 * error * x for error, x in zip(errors, xs)) / len(xs)
        db = sum(2 * error for error in errors) / len(xs)
        weight -= lr * dw
        bias -= lr * db
    return weight, bias

print(train([-2, -1, 0, 1, 2], [-3, -1, 1, 3, 5]))
''', [('Learns slope 2', 'abs(train([-2,-1,0,1,2],[-3,-1,1,3,5])[0]-2)<.01'),
 ('Learns bias 1', 'abs(train([-2,-1,0,1,2],[-3,-1,1,3,5])[1]-1)<.01'),
 ('Learns another relationship', 'abs(train([-1,0,1],[-4,-1,2])[0]-3)<.02'),
 ('Zero epochs leaves initial parameters', 'train([1],[3],epochs=0)==(0,0)'),
 ('Both gradients use the old parameters',
  '(lambda pair: abs(pair[0] - 0.6) < 1e-9 and abs(pair[1] - 0.6) < 1e-9)(train([1], [3], '
  'epochs=1, lr=0.1))')], ['Forward pass','Gradients','Parameter update'],20)

lesson('pytorch',1,'Think in tensors',
'A tensor is a multidimensional array with a shape, data type, and device. PyTorch tensors also carry the information needed for automatic differentiation.',
'[batch, features] @ [features, outputs] → [batch, outputs]',
('A batch of three examples with two features has shape (3, 2). Weights with shape (2, 1) '
 'give one prediction per example. For row [1, 2] and weights [[2], [1]], the product is 1 '
 '× 2 + 2 × 1 = 4. Adding bias 0.5 gives 4.5. The shared dimension disappears because its '
 'products are summed.'),
['Multiply x by weights using tensor matrix multiplication.',
 'Add bias to each result.',
 'Return the tensor from linear_batch(x, weights, bias).'],
'Write down each tensor shape before debugging a matrix operation.',
['Each row of x contains one example. Match its feature count to the first dimension of '
 'weights.',
 'Use the @ operator for matrix multiplication. Bias broadcasts across rows.',
 'Return x @ weights + bias.'],
'''
import torch

def linear_batch(x, weights, bias):
    # Return a tensor of predictions.
    return None

x = torch.tensor([[1., 2.], [3., 4.]])
print(linear_batch(x, torch.tensor([[2.], [1.]]), 0.5))
''',
'''
import torch

def linear_batch(x, weights, bias):
    return x @ weights + bias

x = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
print(linear_batch(x, torch.tensor([[2.0], [1.0]]), 0.5))
''', [('Computes a batch','torch.allclose(linear_batch(torch.tensor([[1.,2.],[3.,4.]]),torch.tensor([[2.],[1.]]),.5),torch.tensor([[4.5],[10.5]]))'),('Preserves output shape','tuple(linear_batch(torch.zeros(3,2),torch.ones(2,4),1).shape)==(3,4)'),('Broadcasts bias per output','torch.allclose(linear_batch(torch.zeros(1,2),torch.ones(2,2),torch.tensor([1.,2.])),torch.tensor([[1.,2.]]))'),('Keeps negative results','torch.allclose(linear_batch(torch.tensor([[-1.]]),torch.tensor([[2.]]),0),torch.tensor([[-2.]]))')], ['x (3, 2)', '@ weights (2, 1)', 'result (3, 1)'])

lesson('pytorch',2,'Let autograd do the math',
('If you create a tensor with requires_grad=True, PyTorch records operations that use it. '
 'Calling backward() on the final single number works back through those operations. Each '
 'derivative is added to the .grad of the tensor you created.'),
'torch.tensor(value, requires_grad=True) → y.backward() → x.grad',
('For y = x² + 3x, the derivative is 2x + 3. At x = 2, that gives 7. The recorded '
 'operations form a graph, which backward() follows in reverse. Create a fresh x for each '
 'call so its gradient starts empty.'),
['Create a floating-point tensor from value with requires_grad=True.',
 'Compute y = x² + 3x and call y.backward().',
 'Return x.grad as a Python float from derivative(value).'],
'Integer tensors cannot require gradients.',
['Create x with torch.tensor(float(value), requires_grad=True).',
 'Set y = x * x + 3 * x, then call y.backward().',
 'Return x.grad.item().'],
'''
import torch

def derivative(value):
    # Return the derivative as a float.
    return None

print(derivative(2))
''',
'''
import torch

def derivative(value):
    x = torch.tensor(float(value), requires_grad=True)
    y = x * x + 3 * x
    y.backward()
    return x.grad.item()

print(derivative(2))
''', [('Derivative at 2 is 7','abs(derivative(2)-7)<1e-6'),('Derivative at -3 is -3','abs(derivative(-3)+3)<1e-6'),('Derivative at 0 is 3','abs(derivative(0)-3)<1e-6'),('Uses backward() to find the gradient','calls("torch.Tensor.backward", lambda: derivative(2))')], ['Record graph','Backward','Read gradient'])

lesson('pytorch',3,'Build a neural network',
('Two Linear layers in a row still compute one linear function. Add ReLU between them to '
 'let the network learn other shapes. ReLU replaces negative values with 0 and keeps '
 'positive values.'),
'Linear(2, 4) → ReLU → Linear(4, 1)',
('The first layer maps two features to four hidden values. ReLU changes a hidden vector '
 'such as [-2, 1, 0, 3] into [0, 1, 0, 3]. The last layer combines those four values into '
 'one output. nn.Sequential runs these layers in order and registers their weights for '
 'training.'),
['Build a torch.nn.Sequential model.',
 'Place ReLU between Linear(2, 4) and Linear(4, 1).',
 'Return the model from make_model().'],
'Inspect list(model). ReLU belongs between the two Linear layers.',
['nn.Sequential accepts layers in the order they run.',
 'The output width of one Linear layer must match the input width of the next.',
 'Return nn.Sequential(nn.Linear(2, 4), nn.ReLU(), nn.Linear(4, 1)).'],
'''
import torch
from torch import nn

def make_model():
    # Return the three-layer model.
    return None

print(make_model())
''',
'''
import torch
from torch import nn

def make_model():
    return nn.Sequential(nn.Linear(2, 4), nn.ReLU(), nn.Linear(4, 1))

print(make_model()(torch.ones(3, 2)))
''', [('Accepts batches', 'tuple(make_model()(torch.ones(3,2)).shape)==(3,1)'),
 ('Registers all 17 parameters', 'sum(p.numel() for p in make_model().parameters())==17'),
 ('Places ReLU between the Linear layers',
  '[type(layer) for layer in make_model()] == [nn.Linear, nn.ReLU, nn.Linear]')], ['2 inputs','4 hidden units','1 output'])

lesson('pytorch',4,'Load data in batches',
('Training usually updates the model after a small group of examples, not after the whole '
 'dataset. A Dataset holds the examples and a DataLoader groups them into batches. Each '
 'batch keeps features paired with their labels. Here TensorDataset keeps every example in '
 'memory; batching limits how many examples each update uses.'),
'TensorDataset(features, labels) → DataLoader → batches',
('For five examples and batch size 2, the batches have sizes 2, 2, and 1. Keeping the last '
 'batch includes every example. With shuffle=False, concatenating the batches gives the '
 'original order. A minibatch is simply one of these smaller groups used for a training '
 'update.'),
['Pair x and y with TensorDataset.',
 'Wrap that dataset in DataLoader using batch_size and shuffle=False.',
 'Return the loader from make_loader(x, y, batch_size), keeping the final partial batch.'],
'Try five numbered examples with batch size 2. Inspect both their order and the last batch.',
['TensorDataset(x, y) keeps each feature and label together.',
 'Pass that dataset and batch_size to DataLoader.',
 'Return DataLoader(TensorDataset(x, y), batch_size=batch_size, shuffle=False, '
 'drop_last=False).'],
'''
import torch
from torch.utils.data import TensorDataset, DataLoader

def make_loader(x, y, batch_size):
    # Return a DataLoader of paired batches.
    return None

print(make_loader(torch.arange(5), torch.arange(5) * 2, 2))
''',
'''
import torch
from torch.utils.data import TensorDataset, DataLoader

def make_loader(x, y, batch_size):
    return DataLoader(TensorDataset(x, y), batch_size=batch_size, shuffle=False)
''', [('Yields three batches for five examples',
  'len(list(make_loader(torch.arange(5),torch.arange(5),2)))==3'),
 ('Retains last partial batch',
  'len(list(make_loader(torch.arange(5),torch.arange(5),2))[-1][0])==1'),
 ('Keeps features and labels paired',
  'all(torch.equal(a*2,b) for a,b in make_loader(torch.arange(5),torch.arange(5)*2,2))'),
 ('Keeps the original example order',
  '(lambda loader: isinstance(loader.sampler, torch.utils.data.SequentialSampler) and '
  'torch.equal(torch.cat([a for a, b in loader]), '
  'torch.arange(7)))(make_loader(torch.arange(7), torch.arange(7), 3))')], ['Dataset','DataLoader','Minibatch'])

lesson('pytorch',5,'Make one optimizer step',
('A training step changes parameters using the current prediction error. Clear old '
 'gradients, compute predictions and loss, call backward(), then let the optimizer update '
 'the parameters.'),
'zero_grad → forward → loss → backward → step',
(('backward() computes the gradients. optimizer.step() uses them to change the weights. For '
 'weight 0, input 1, and target 2, MSE is 4 and the gradient is −4. Stochastic gradient '
 'descent (SGD) subtracts learning rate times gradient. With learning rate 0.1, the weight '
 'becomes 0.4. Return the loss measured before that update.')),
['Clear old gradients with optimizer.zero_grad().',
 'Compute torch.nn.functional.mse_loss(model(x), y), call backward(), then '
 'optimizer.step().',
 'Return the pre-update loss as a float from train_step(model, optimizer, x, y).'],
('Call backward() on the loss tensor. The float returned by loss.item() has no gradient '
 'information.'),
['Keep the loss tensor until you finish backward().',
 'Set loss = torch.nn.functional.mse_loss(model(x), y).',
 'Call loss.backward(), then optimizer.step(), then return loss.item().'],
'''
import torch

def train_step(model, optimizer, x, y):
    # Update the model and return the loss before the update.
    return None

model = torch.nn.Linear(1, 1)
optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
print(train_step(model, optimizer, torch.tensor([[1.]]), torch.tensor([[2.]])))
''',
'''
import torch

def train_step(model, optimizer, x, y):
    optimizer.zero_grad()
    loss = torch.nn.functional.mse_loss(model(x), y)
    loss.backward()
    optimizer.step()
    return loss.item()
''', [('Returns the scalar loss','check_torch_step(train_step, "loss")'),('Updates weight using the gradient','check_torch_step(train_step, "update")'),('Clears gradients between steps','check_torch_step(train_step, "clear")')], ['Clear gradients','Backpropagate','Optimizer step'])

lesson('pytorch',6,'Train a small regressor',
('A regressor predicts a number, such as a price or temperature. Train a PyTorch regressor '
 'on y = 2x + 1 by repeating the optimizer step from the previous lesson.'),
'nn.Linear → mean squared error → SGD update → repeat',
('The five training inputs run from −2 to 2. Once the model learns weight 2 and bias 1, it '
 'should also predict 7 for the new input 3. SGD means stochastic gradient descent, an '
 'optimizer that subtracts learning rate times gradient. Here every update uses all five '
 'examples.'),
['Create nn.Linear(1, 1) with the starter’s fixed random seed.',
 'Train on x = [-2, -1, 0, 1, 2] and y = 2x + 1 for 200 steps with SGD at learning rate 0.05.',
 'Call model.eval() and return the trained model from fit_model().'],
'Shape x as five rows with one value each. A flat vector does not match Linear(1, 1).',
['Shape x as (5, 1), then set y = 2 * x + 1.','Repeat zero_grad, MSE, backward, and step.','Call model.eval() and return the model.'],
'''
import torch
from torch import nn

def fit_model():
    torch.manual_seed(7)
    model = nn.Linear(1, 1)
    # Train and return this model in evaluation mode.
    return model

print(fit_model())
''',
'''
import torch
from torch import nn

def fit_model():
    torch.manual_seed(7)
    model = nn.Linear(1, 1)
    x = torch.tensor([[-2.0], [-1.0], [0.0], [1.0], [2.0]])
    y = 2 * x + 1
    optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
    for _ in range(200):
        optimizer.zero_grad()
        loss = nn.functional.mse_loss(model(x), y)
        loss.backward()
        optimizer.step()
    model.eval()
    return model

print(fit_model()(torch.tensor([[3.0]])))
''', [('Generalizes to x=3','abs(fit_model()(torch.tensor([[3.]])).item()-7)<.03'),('Generalizes to negative input','abs(fit_model()(torch.tensor([[-3.]])).item()+5)<.03'),('Uses evaluation mode','fit_model().training is False')], ['Training data','Learned weights','Unseen input'],20)

lesson('tensorflow',1,'Tensors, the TensorFlow way',
('A tensor is an array with a shape and a data type. TensorFlow uses tf.Tensor for fixed '
 'values and tf.Variable for values that training can change. Matrix multiplication '
 'follows the same shape rules as in NumPy.'),
'[batch, features] × [features, outputs] + bias',
('A row [1, 2] multiplied by weights [[2], [1]] gives 1 × 2 + 2 × 1 = 4. Adding bias 0.5 '
 'gives 4.5. Use tf.matmul for this operation. A .numpy() copy is useful for printing, but '
 'TensorFlow cannot track gradients through calculations done in NumPy.'),
['Multiply x by weights with tf.matmul.',
 'Add bias to the product.',
 'Return the TensorFlow tensor from linear_batch(x, weights, bias).'],
'The last dimension of x must equal the first dimension of weights.',
['Check that the two feature dimensions match.',
 'tf.matmul(x, weights) sums the products for each row.',
 'Return tf.matmul(x, weights) + bias.'],
'''
import tensorflow as tf

def linear_batch(x, weights, bias):
    # Return a tensor of predictions.
    return None

print(linear_batch(tf.constant([[1., 2.]]), tf.constant([[2.], [1.]]), 0.5))
''',
'''
import tensorflow as tf

def linear_batch(x, weights, bias):
    return tf.matmul(x, weights) + bias
''', [('Correct matrix product','bool(tf.reduce_all(tf.abs(linear_batch(tf.constant([[1.,2.]]),tf.constant([[2.],[1.]]),.5)-4.5)<1e-6))'),('Preserves batch and output dimensions','tuple(linear_batch(tf.zeros((3,2)),tf.ones((2,4)),1).shape)==(3,4)'),('Returns a tensor','tf.is_tensor(linear_batch(tf.zeros((1,2)),tf.ones((2,1)),0))')], ['x (3, 2)', 'weights (2, 1)', 'result (3, 1)'])

lesson('tensorflow',2,'Record with GradientTape',
('To find a gradient, TensorFlow must record the calculation that produced the loss. '
 'GradientTape records operations inside its with block, then computes their derivatives.'),
'with tf.GradientTape() as tape: ...',
('For x² + 3x at x = 2, the derivative is 2 × 2 + 3 = 7. A trainable tf.Variable is '
 'watched automatically, meaning the tape tracks calculations that use it. Ask for the '
 'derivative after the calculation. Keep the calculation inside the tape so there are '
 'operations to follow.'),
['Create a floating-point tf.Variable from value.',
 'Compute x² + 3x inside a GradientTape context.',
 'Return the derivative as a Python float from derivative(value).'],
'A None gradient often means the computation was outside the tape or detached.',
['Set x = tf.Variable(float(value)).',
 'Inside with tf.GradientTape() as tape, set loss = x * x + 3 * x.',
 'Return float(tape.gradient(loss, x).numpy()).'],
'''
import tensorflow as tf

def derivative(value):
    # Return the derivative as a float.
    return None

print(derivative(2))
''',
'''
import tensorflow as tf

def derivative(value):
    x = tf.Variable(float(value))
    with tf.GradientTape() as tape:
        loss = x * x + 3 * x
    return float(tape.gradient(loss, x).numpy())
''', [('Derivative at 2','abs(derivative(2)-7)<1e-6'),('Derivative at -3','abs(derivative(-3)+3)<1e-6'),('Derivative at zero','abs(derivative(0)-3)<1e-6')], ['Tape context','Forward expression','tape.gradient'])

lesson('tensorflow',3,'Compose a Keras model',
('Keras Sequential runs layers in order. Put ReLU, which replaces negative values with '
 'zero, in the hidden layer. A linear output can then predict either positive or negative '
 'numbers.'),
'Input(2) → Dense(4, relu) → Dense(1)',
('Two inputs feed four hidden units, then those four values feed one output. Keras calls '
 'each Dense layer’s weight matrix its kernel. It has shape (inputs, outputs), so the '
 'first layer has 2 × 4 weights and 4 biases. The output has 4 weights and 1 bias, for 17 '
 'trainable numbers in total.'),
['Start a tf.keras.Sequential model with tf.keras.Input(shape=(2,)).',
 'Add Dense(4, activation="relu") and a Dense(1) layer with a linear output.',
 'Return the model from make_model().'],
'A ReLU output would prevent predictions below zero. Leave the output activation linear.',
['Input(shape=(2,)) describes one example with two features.',
 'Use four hidden units with ReLU, followed by one output unit.',
 'Return tf.keras.Sequential([tf.keras.Input(shape=(2,)), tf.keras.layers.Dense(4, '
 'activation="relu"), tf.keras.layers.Dense(1)]).'],
'''
import tensorflow as tf

def make_model():
    # Return the model.
    return None

print(make_model())
''',
'''
import tensorflow as tf

def make_model():
    return tf.keras.Sequential([
        tf.keras.Input(shape=(2,)),
        tf.keras.layers.Dense(4, activation="relu"),
        tf.keras.layers.Dense(1),
    ])
''', [('Correct batch output shape', 'tuple(make_model()(tf.ones((3,2))).shape)==(3,1)'),
 ('Registers 17 scalar parameters', 'make_model().count_params()==17'),
 ('Hidden layer uses ReLU', 'make_model().layers[0].activation.__name__=="relu"'),
 ('Keeps the output activation linear',
  'make_model().layers[-1].activation.__name__ == "linear"')], ['Input layer','Dense + ReLU','Dense output'])

lesson('tensorflow',4,'Build a tf.data pipeline',
('A tf.data.Dataset supplies examples to a training loop. Create it from paired features '
 'and labels, then group those pairs into batches.'),
'from_tensor_slices → batch → iterate',
('Five examples with batch size 2 produce batches of sizes 2, 2, and 1. Each label travels '
 'with its feature. Keeping the final partial batch ensures the fifth example is used. '
 'Iterating this dataset preserves the input order.'),
['Create a dataset with tf.data.Dataset.from_tensor_slices((x, y)).',
 'Group examples with the supplied batch_size, preserving order and the last partial '
 'batch.',
 'Return the dataset from make_dataset(x, y, batch_size).'],
'Print the last batch for five examples and batch size 2. It should contain one example.',
['Build the dataset from the pair (x, y) so their rows stay together.',
 'Call batch on the dataset after creating it.',
 'Return tf.data.Dataset.from_tensor_slices((x, y)).batch(batch_size, '
 'drop_remainder=False).'],
'''
import tensorflow as tf

def make_dataset(x, y, batch_size):
    # Return a dataset of paired batches.
    return None

print(make_dataset(tf.range(5), tf.range(5) * 2, 2))
''',
'''
import tensorflow as tf

def make_dataset(x, y, batch_size):
    return tf.data.Dataset.from_tensor_slices((x, y)).batch(batch_size, drop_remainder=False)
''', [('Three batches for five examples','len(list(make_dataset(tf.range(5),tf.range(5),2)))==3'),('Retains the last example','len(list(make_dataset(tf.range(5),tf.range(5),2))[-1][0])==1'),('Maintains paired labels','all(bool(tf.reduce_all(a*2==b)) for a,b in make_dataset(tf.range(5),tf.range(5)*2,2))')], ['Paired tensors','Dataset','Batches'])

lesson('tensorflow',5,'Apply gradients yourself',
('A custom training step lets you choose how to compute loss and update a variable. Record '
 'the loss with GradientTape, request its gradient, then pass that gradient and variable '
 'to the optimizer.'),
'tape.gradient(loss, variables) → optimizer.apply_gradients',
(('With weight 0, x = 1, and y = 2, the prediction is 0 and mean squared error is 4. The '
 'gradient is −4. Stochastic gradient descent (SGD) subtracts learning rate times '
 'gradient. At learning rate 0.1, it changes the weight to 0.4. The loss returned by this '
 'step is still 4 because it was measured before the update.')),
['Compute predictions weight * x and their mean squared error inside a GradientTape.',
 'Find the gradient with respect to weight and apply it with optimizer.apply_gradients.',
 'Return the pre-update loss as a float from train_step(weight, optimizer, x, y).'],
('Pass (gradient, weight) to apply_gradients. Swapping the pair gives the optimizer the '
 'wrong object to update.'),
['Inside the tape, set loss = tf.reduce_mean(tf.square(weight * x - y)).',
 'After the tape block, set grad = tape.gradient(loss, weight).',
 'Call optimizer.apply_gradients([(grad, weight)]), then return float(loss.numpy()).'],
'''
import tensorflow as tf

def train_step(weight, optimizer, x, y):
    # Update weight and return the loss before the update.
    return None

weight = tf.Variable(0.)
optimizer = tf.keras.optimizers.SGD(0.1)
print(train_step(weight, optimizer, tf.constant([1.]), tf.constant([2.])))
''',
'''
import tensorflow as tf

def train_step(weight, optimizer, x, y):
    with tf.GradientTape() as tape:
        loss = tf.reduce_mean(tf.square(weight * x - y))
    grad = tape.gradient(loss, weight)
    optimizer.apply_gradients([(grad, weight)])
    return float(loss.numpy())
''', [('Returns loss before update','check_tf_step(train_step,"loss")'),('Applies the correct gradient','check_tf_step(train_step,"update")'),('Updates consistently on a second step','check_tf_step(train_step,"twice")')], ['Record loss','Compute gradient','Apply gradient'])

lesson('tensorflow',6,'Train with Keras',
('Keras can manage the training step after you choose an optimizer and a loss. Train the '
 'line y = 2x + 1 from the Foundations path using a single Dense layer.'),
'build → compile → train_on_batch → predict',
('Compile tells Keras how to calculate error and change weights. Each train_on_batch call '
 'performs one update on the supplied examples. With weight 2 and bias 1, the model '
 'predicts 7 for input 3, outside the training inputs. Calling the model after training '
 'lets you check that prediction.'),
['Build a Keras model with Input(shape=(1,)) and one Dense(1) layer.',
 'Compile with SGD(learning_rate=0.05) and loss="mse". Call model.train_on_batch 200 times '
 'on x = [-2, -1, 0, 1, 2] and y = 2x + 1.',
 'Return the trained model from fit_model().'],
'compile() sets the training rules. The weights change only when train_on_batch runs.',
['Make x a tensor with shape (5, 1), using the five training inputs.',
 'Call model.compile(optimizer=tf.keras.optimizers.SGD(0.05), loss="mse").',
 'In a loop of 200 iterations, call model.train_on_batch(x, 2 * x + 1). Return model.'],
'''
import tensorflow as tf

def fit_model():
    tf.keras.utils.set_random_seed(7)
    model = tf.keras.Sequential([tf.keras.Input(shape=(1,)), tf.keras.layers.Dense(1)])
    # Compile, train, and return this model.
    return model

print(fit_model())
''',
'''
import tensorflow as tf

def fit_model():
    tf.keras.utils.set_random_seed(7)
    model = tf.keras.Sequential([tf.keras.Input(shape=(1,)), tf.keras.layers.Dense(1)])
    model.compile(optimizer=tf.keras.optimizers.SGD(0.05), loss='mse')
    x = tf.constant([[-2.0], [-1.0], [0.0], [1.0], [2.0]])
    for _ in range(200):
        model.train_on_batch(x, 2 * x + 1)
    return model
''', [('Predicts an unseen positive input','abs(float(fit_model()(tf.constant([[3.]]),training=False).numpy()[0,0])-7)<.04'),('Predicts an unseen negative input','abs(float(fit_model()(tf.constant([[-3.]]),training=False).numpy()[0,0])+5)<.04'),('Produces one output per sample','tuple(fit_model()(tf.zeros((4,1))).shape)==(4,1)')], ['Compile','Train batches','Evaluate'],20)

from courses_extra import COURSES_EXTRA, LESSONS_EXTRA
COURSES.extend(COURSES_EXTRA)
LESSONS.extend(LESSONS_EXTRA)

from engineering_courses import COURSES_ENGINEERING, LESSONS_ENGINEERING
COURSES.extend(COURSES_ENGINEERING)
LESSONS.extend(LESSONS_ENGINEERING)

from lesson_guides import GUIDES, ORIENTATION
for course in COURSES:course['orientation']=ORIENTATION[course['id']]
for item in LESSONS:item['example']=GUIDES[item['id']]

BY_ID={lesson['id']:lesson for lesson in LESSONS}

from functools import cache
from glossary import GLOSSARY, lesson_texts, linked_terms

# The curriculum does not change while the server runs, so it is built once.
@cache
def public_curriculum():
    lessons=[{k:v for k,v in lesson.items() if k not in ('solution','checks')} | {
        'checkLabels':[c['label'] for c in lesson['checks']],
        # Glossary terms in the intro and explanation, in order of first appearance.
        'glossary':linked_terms(lesson_texts(lesson),lesson['course'])} for lesson in LESSONS]
    glossary=[{k:v for k,v in entry.items() if k!='paths'} for entry in GLOSSARY]
    return {'courses':COURSES,'lessons':lessons,'glossary':glossary}
