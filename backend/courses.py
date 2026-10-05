"""Original, offline curriculum and executable reference answers."""
from textwrap import dedent

COURSES = [
    dict(id='foundations', title='ML foundations', subtitle='The ideas behind every framework', icon='book', color='green'),
    dict(id='pytorch', title='PyTorch', subtitle='Tensors, autograd and training loops', icon='flame', color='orange'),
    dict(id='tensorflow', title='TensorFlow', subtitle='The same ideas with TensorFlow & Keras', icon='box', color='blue'),
]
LESSONS = []

def lesson(course, number, title, intro, concept, explanation, tasks, tip, hints, starter, solution, checks, diagram=None, minutes=12):
    refs = {'foundations': ('Google ML Crash Course', 'https://developers.google.com/machine-learning/crash-course/linear-regression'), 'pytorch': ('PyTorch: Learn the Basics', 'https://docs.pytorch.org/tutorials/beginner/basics/intro.html'), 'tensorflow': ('TensorFlow: automatic differentiation', 'https://www.tensorflow.org/guide/autodiff')}
    name,url=refs[course]
    LESSONS.append(dict(id=f'{course}-{number}', course=course, title=title, minutes=minutes, xp=150 if number==6 else 100, intro=intro, concept=concept, explanation=explanation, tasks=tasks, tip=tip, hints=hints, starter=dedent(starter).strip()+'\n', solution=dedent(solution).strip()+'\n', checks=[dict(label=a,expr=b) for a,b in checks], diagram=diagram or ['Data','Model','Prediction'], reference=dict(title=name,url=url)))

lesson('foundations',1,'Your first prediction',
'A model is a function with parameters you can learn from data. Start with the simplest one: a straight line.',
'prediction = weight × input + bias',
'Weight controls how much the output changes when the input increases by one. Bias shifts every prediction by the same amount. For x = 3, weight = 2 and bias = 1, the prediction is 7. Today you set the parameters; later, a training loop will learn them.',
['Write predict(x, weight, bias).','Return the linear prediction.','Run your code, then check your work.'],
'Think of weight as sensitivity and bias as the starting point.',
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
'For predictions [2, 4] and targets [1, 6], the squared errors are [1, 4] and MSE is 2.5. Loss is a training signal, not necessarily the business metric. Squaring removes the sign; it does not tell you which direction to adjust a weight.',
['Implement mse(predictions, targets).','Return the mean of squared differences.','Reject empty or unequal-length lists with ValueError.'],
'Always define how your data functions handle invalid shapes.',
['Pair predictions and targets with zip.','Sum squared differences, then divide by the number of pairs.','Validate lengths before computing sum((p-t)**2 for p,t in zip(...)).'],
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
    return sum((p-t)**2 for p,t in zip(predictions, targets))/len(targets)

print(mse([2, 4], [1, 6]))
''', [('MSE is 2.5','mse([2,4],[1,6])==2.5'),('Perfect predictions have zero loss','mse([1,2],[1,2])==0'),('Symmetric errors','mse([-2,2],[0,0])==4'),('Empty lists rejected',"raises(ValueError, lambda: mse([],[]))"),('Mismatched lists rejected',"raises(ValueError, lambda: mse([1],[1,2]))")], ['Predict','Compare','Average error'])

lesson('foundations',3,'Follow the gradient',
'The gradient tells you how loss changes when a parameter changes. Gradient descent takes a small step in the opposite direction.\n\nFor loss (w − target)², the derivative with respect to w is 2(w − target).',
'w_next = w − learning_rate × gradient',
'The learning rate controls the step size. A very small value learns slowly; a very large value can overshoot or diverge. Try the interactive plot below. Notice that a low loss alone is not proof that a model will generalize.',
['Implement step(weight, target, learning_rate).','Compute the derivative of (weight − target)².','Return the updated weight, without mutating other state.'],
'A positive gradient means loss rises as the weight rises. Step left.',
['The derivative is 2 * (weight - target).','Subtract learning_rate times that derivative.','Return weight - learning_rate * 2 * (weight - target).'],
'''
def step(weight, target, learning_rate):
    return None

print(step(0, 3, 0.1))
''',
'''
def step(weight, target, learning_rate):
    return weight - learning_rate * 2 * (weight - target)

print(step(0, 3, 0.1))
''', [('Moves toward target','abs(step(0,3,.1)-.6)<1e-9'),('Moves down when above target','abs(step(5,3,.1)-4.6)<1e-9'),('Zero gradient leaves weight unchanged','step(3,3,.1)==3'),('Zero learning rate freezes training','step(1,3,0)==1')], ['Loss','Gradient','Update'])

lesson('foundations',4,'Train, validate, test',
'You need data the model has never trained on to estimate generalization. Use training data to fit weights, validation data to choose settings, and test data once for a final evaluation.',
'fit on train → choose with validation → report on test',
'This exercise preserves order so the split is reproducible. For time-dependent data, that ordering is often essential: future observations must not leak into past training. For independent samples, shuffle with a fixed seed before splitting. Split before fitting preprocessing statistics.',
['Write split_data(rows).','Use the first 60% for training and the next 20% for validation (integer boundaries).','Return (train, validation, test) without modifying rows.'],
'Leakage can produce excellent evaluation scores and a useless deployed model.',
['Use slice boundaries int(len(rows) * 0.6) and int(len(rows) * 0.8).','The last slice contains all remaining rows.','Return rows[:a], rows[a:b], rows[b:].'],
'''
def split_data(rows):
    return None

print(split_data(list(range(10))))
''',
'''
def split_data(rows):
    a, b = int(len(rows)*0.6), int(len(rows)*0.8)
    return rows[:a], rows[a:b], rows[b:]

print(split_data(list(range(10))))
''', [('60/20/20 for ten rows','split_data(list(range(10)))==(list(range(6)),[6,7],[8,9])'),('No dropped rows for odd size','sum((list(x) for x in split_data(list(range(7)))),[])==list(range(7))'),('Empty input stays empty','split_data([])==([],[],[])')], ['Training','Validation','Test'])

lesson('foundations',5,'Scale your features',
'Features measured in very different units can make optimization harder. Standardization subtracts the training mean and divides by the training standard deviation.',
'z = (x − training_mean) / training_std',
'Fit the mean and standard deviation on the training set only. Reuse those exact values for validation, test, and future inference. Here we use population standard deviation. Constant features get scale 1 so they map to zero without dividing by zero.',
['Write standardize(train, values).','Compute mean and population standard deviation from train.','Return the transformed values; use scale 1 for constant training data.'],
'The preprocessing state is part of your trained model.',
['Compute the mean of train, not values.','Variance is the mean squared distance to that mean.','Use variance ** 0.5 or 1.0 for the scale.'],
'''
def standardize(train, values):
    return None

print(standardize([1, 3], [1, 3, 5]))
''',
'''
def standardize(train, values):
    if not train:
        raise ValueError('Training data cannot be empty')
    mean=sum(train)/len(train)
    scale=(sum((x-mean)**2 for x in train)/len(train))**0.5 or 1.0
    return [(x-mean)/scale for x in values]

print(standardize([1, 3], [1, 3, 5]))
''', [('Uses training statistics','standardize([1,3],[1,3,5])==[-1,1,3]'),('Handles constant feature','standardize([4,4],[4,5])==[0,1]'),('Transforms empty evaluation set','standardize([1,2],[])==[]')], ['Fit statistics','Save statistics','Transform'])

lesson('foundations',6,'A complete training loop',
'Bring the pieces together: predict, measure error, compute gradients, update parameters, repeat.\n\nTrain a line on the tiny dataset y = 2x + 1. We deliberately use small synthetic data so you can understand every operation.',
'dw = mean(2 × error × x)   db = mean(2 × error)',
'An epoch is one pass over the training set. This exercise uses a full-batch update: all examples contribute to each gradient. Evaluate both gradients using the old weight and bias, then update. Frameworks will automate derivatives, but the loop still follows this structure.',
['Implement train(xs, ys, epochs=400, lr=0.05).','Start weight and bias at zero; minimize MSE with the formulas above.','Return the learned (weight, bias).'],
'Compute both gradients before updating either parameter.',
['Build errors with w*x+b-y for each pair.','Average 2*error*x and 2*error.','For each epoch: w -= lr*dw; b -= lr*db.'],
'''
def train(xs, ys, epochs=400, lr=0.05):
    weight, bias = 0.0, 0.0
    # Repeat the learning loop.
    return weight, bias

print(train([-2, -1, 0, 1, 2], [-3, -1, 1, 3, 5]))
''',
'''
def train(xs, ys, epochs=400, lr=0.05):
    w,b=0.0,0.0
    for _ in range(epochs):
        errors=[w*x+b-y for x,y in zip(xs,ys)]
        dw=sum(2*e*x for e,x in zip(errors,xs))/len(xs)
        db=sum(2*e for e in errors)/len(xs)
        w,b=w-lr*dw,b-lr*db
    return w,b

print(train([-2,-1,0,1,2],[-3,-1,1,3,5]))
''', [('Learns slope 2','abs(train([-2,-1,0,1,2],[-3,-1,1,3,5])[0]-2)<.01'),('Learns bias 1','abs(train([-2,-1,0,1,2],[-3,-1,1,3,5])[1]-1)<.01'),('Learns another relationship','abs(train([-1,0,1],[-4,-1,2])[0]-3)<.02'),('Zero epochs leaves initial parameters','train([1],[3],epochs=0)==(0,0)')], ['Forward pass','Gradients','Parameter update'],20)

lesson('pytorch',1,'Think in tensors',
'A tensor is a multidimensional array with a shape, data type, and device. PyTorch tensors also carry the information needed for automatic differentiation.',
'[batch, features] @ [features, outputs] → [batch, outputs]',
'A batch of three examples with two features has shape (3, 2). A weight matrix (2, 1) maps it to one prediction per example. Matrix multiplication contracts the shared dimension. Elementwise multiplication does something different.',
['Implement linear_batch(x, weights, bias).','Use tensor matrix multiplication and add bias.','Keep the result as a tensor; do not convert to a Python list.'],
'Write down each tensor shape before debugging a matrix operation.',
['PyTorch supports the @ operator.','The bias broadcasts across the batch dimension.','Return x @ weights + bias.'],
'''
import torch

def linear_batch(x, weights, bias):
    return None

x = torch.tensor([[1., 2.], [3., 4.]])
print(linear_batch(x, torch.tensor([[2.], [1.]]), 0.5))
''',
'''
import torch

def linear_batch(x, weights, bias):
    return x @ weights + bias

x=torch.tensor([[1.,2.],[3.,4.]])
print(linear_batch(x,torch.tensor([[2.],[1.]]),0.5))
''', [('Computes a batch','torch.allclose(linear_batch(torch.tensor([[1.,2.],[3.,4.]]),torch.tensor([[2.],[1.]]),.5),torch.tensor([[4.5],[10.5]]))'),('Preserves output shape','tuple(linear_batch(torch.zeros(3,2),torch.ones(2,4),1).shape)==(3,4)'),('Broadcasts bias per output','torch.allclose(linear_batch(torch.zeros(1,2),torch.ones(2,2),torch.tensor([1.,2.])),torch.tensor([[1.,2.]]))')])

lesson('pytorch',2,'Let autograd do the math',
'PyTorch records operations on tensors that require gradients. Calling backward on a scalar result walks the graph and accumulates derivatives on leaf tensors.',
'x.requires_grad_(True) → loss.backward() → x.grad',
'For f(x)=x²+3x, the derivative is 2x+3. Create a fresh floating-point leaf tensor for each call. Repeated backward calls on the same parameter accumulate gradients; training loops must clear them each step.',
['Implement derivative(value).','Use a tensor with requires_grad=True and differentiate x²+3x with backward().','Return the derivative as a Python float.'],
'Integer tensors cannot require gradients.',
['Create torch.tensor(float(value), requires_grad=True).','Compute loss = x*x + 3*x, then loss.backward().','Return x.grad.item().'],
'''
import torch

def derivative(value):
    return None

print(derivative(2))
''',
'''
import torch

def derivative(value):
    x=torch.tensor(float(value),requires_grad=True)
    (x*x+3*x).backward()
    return x.grad.item()

print(derivative(2))
''', [('Derivative at 2 is 7','abs(derivative(2)-7)<1e-6'),('Derivative at -3 is -3','abs(derivative(-3)+3)<1e-6'),('Derivative at 0 is 3','abs(derivative(0)-3)<1e-6')], ['Record graph','Backward','Read gradient'])

lesson('pytorch',3,'Build a neural network',
'A neural network composes parameterized layers with nonlinear functions. Without nonlinearities, a stack of linear layers still represents a linear function.',
'Linear(2, 4) → ReLU → Linear(4, 1)',
'nn.Module registers trainable parameters and submodules so optimizers can find them. nn.Sequential is ideal for a straight pipeline. The first dimension is the batch; Linear transforms the last dimension.',
['Implement make_model() using torch.nn.','Build a 2-input, 4-hidden-unit, 1-output network with ReLU in the middle.','Return the model, without training it.'],
'A model definition does not mean the model has learned anything yet.',
['Use nn.Sequential to compose layers.','Use nn.Linear(2,4), nn.ReLU(), nn.Linear(4,1).','The network has 12 + 5 = 17 trainable scalar parameters.'],
'''
import torch
from torch import nn

def make_model():
    return None

# model = make_model()
# print(model(torch.ones(3, 2)))
''',
'''
import torch
from torch import nn

def make_model():
    return nn.Sequential(nn.Linear(2,4),nn.ReLU(),nn.Linear(4,1))

print(make_model()(torch.ones(3,2)))
''', [('Accepts batches','tuple(make_model()(torch.ones(3,2)).shape)==(3,1)'),('Registers all 17 parameters','sum(p.numel() for p in make_model().parameters())==17'),('Includes a ReLU nonlinearity','any(isinstance(m,nn.ReLU) for m in make_model().modules())')], ['2 inputs','4 hidden units','1 output'])

lesson('pytorch',4,'Load data in batches',
'A Dataset describes your examples. A DataLoader batches and optionally shuffles them. Keeping those responsibilities separate makes training code reusable.',
'TensorDataset(features, labels) → DataLoader → batches',
'Minibatches trade off memory and gradient noise. The final batch may be smaller than the others; do not silently drop it unless that is intentional. This exercise keeps ordering fixed so you can inspect the batches.',
['Implement make_loader(x, y, batch_size).','Wrap the tensors in a TensorDataset and use DataLoader with shuffle=False.','Keep the last partial batch.'],
'Batch size changes memory use; it is not the number of training epochs.',
['Import TensorDataset and DataLoader from torch.utils.data.','DataLoader accepts a dataset and batch_size.','Use drop_last=False (the default).'],
'''
import torch
from torch.utils.data import TensorDataset, DataLoader

def make_loader(x, y, batch_size):
    return None
''',
'''
import torch
from torch.utils.data import TensorDataset, DataLoader

def make_loader(x, y, batch_size):
    return DataLoader(TensorDataset(x,y),batch_size=batch_size,shuffle=False)
''', [('Yields three batches for five examples','len(list(make_loader(torch.arange(5),torch.arange(5),2)))==3'),('Retains last partial batch','len(list(make_loader(torch.arange(5),torch.arange(5),2))[-1][0])==1'),('Keeps features and labels paired','all(torch.equal(a*2,b) for a,b in make_loader(torch.arange(5),torch.arange(5)*2,2))')], ['Dataset','DataLoader','Minibatch'])

lesson('pytorch',5,'Make one optimizer step',
'Training is a sequence of explicit actions: clear old gradients, calculate predictions and loss, backpropagate, then update parameters.',
'zero_grad → forward → loss → backward → step',
'An optimizer owns the update rule, but it does not compute gradients. Use MSELoss here. Return the loss measured before the update as a float; keep the graph intact until backward finishes.',
['Implement train_step(model, optimizer, x, y).','Clear gradients, compute MSE, backpropagate, and call optimizer.step().','Return the pre-update scalar loss.'],
'Calling loss.item() before backward is fine if you keep the original loss tensor too.',
['optimizer.zero_grad() belongs before backward.','loss = torch.nn.functional.mse_loss(model(x), y).','loss.backward(); optimizer.step(); return loss.item().'],
'''
import torch

def train_step(model, optimizer, x, y):
    return None
''',
'''
import torch

def train_step(model, optimizer, x, y):
    optimizer.zero_grad()
    loss=torch.nn.functional.mse_loss(model(x),y)
    loss.backward()
    optimizer.step()
    return loss.item()
''', [('Returns the scalar loss','check_torch_step(train_step, "loss")'),('Updates weight using the gradient','check_torch_step(train_step, "update")'),('Clears gradients between steps','check_torch_step(train_step, "clear")')], ['Clear gradients','Backpropagate','Optimizer step'])

lesson('pytorch',6,'Train a small regressor',
'Build and train a complete PyTorch regressor on y = 2x + 1. This is a tiny, deterministic capstone with the same mechanics as a larger training job.',
'nn.Linear → MSELoss → SGD → repeat',
'Use CPU and a fixed seed for reproducibility. The returned model should produce accurate predictions on unseen values. In a real project you would also save the state_dict, preprocessing state, framework versions and validation metrics.',
['Implement fit_model() that returns a trained nn.Linear(1,1).','Train on x=[-2,-1,0,1,2] and y=2x+1 for 200 steps with SGD at lr=0.05.','Set the model to eval mode before returning it.'],
'model.eval() changes layer behavior; torch.no_grad() separately disables gradient recording.',
['Shape x as (5,1), then set y=2*x+1.','Repeat zero_grad, MSE, backward, and step.','Call model.eval() and return the model.'],
'''
import torch
from torch import nn

def fit_model():
    torch.manual_seed(7)
    model = nn.Linear(1, 1)
    # Train this model.
    return model
''',
'''
import torch
from torch import nn

def fit_model():
    torch.manual_seed(7)
    model=nn.Linear(1,1)
    x=torch.tensor([[-2.],[-1.],[0.],[1.],[2.]])
    y=2*x+1
    optimizer=torch.optim.SGD(model.parameters(),lr=.05)
    for _ in range(200):
        optimizer.zero_grad()
        loss=nn.functional.mse_loss(model(x),y)
        loss.backward()
        optimizer.step()
    model.eval()
    return model

print(fit_model()(torch.tensor([[3.]])))
''', [('Generalizes to x=3','abs(fit_model()(torch.tensor([[3.]])).item()-7)<.03'),('Generalizes to negative input','abs(fit_model()(torch.tensor([[-3.]])).item()+5)<.03'),('Uses evaluation mode','fit_model().training is False')], ['Training data','Learned weights','Unseen input'],20)

lesson('tensorflow',1,'Tensors, the TensorFlow way',
'The shape rules are the same; the API changes. TensorFlow uses tf.Tensor for immutable values and tf.Variable for mutable state such as model parameters.',
'[batch, features] × [features, outputs] + bias',
'Use tf.matmul for matrix multiplication. Most eager tensors expose .numpy() for inspection, but converting to NumPy inside a differentiable calculation disconnects the gradient path. Keep the result as a TensorFlow tensor.',
['Implement linear_batch(x, weights, bias).','Multiply using tf.matmul and add the bias.','Return a TensorFlow tensor.'],
'Translate the concept first, then look up the framework spelling.',
['tf.matmul(x, weights) performs the contraction.','Bias broadcasting works across batches.','Return tf.matmul(x, weights) + bias.'],
'''
import tensorflow as tf

def linear_batch(x, weights, bias):
    return None
''',
'''
import tensorflow as tf

def linear_batch(x, weights, bias):
    return tf.matmul(x,weights)+bias
''', [('Correct matrix product','bool(tf.reduce_all(tf.abs(linear_batch(tf.constant([[1.,2.]]),tf.constant([[2.],[1.]]),.5)-4.5)<1e-6))'),('Preserves batch and output dimensions','tuple(linear_batch(tf.zeros((3,2)),tf.ones((2,4)),1).shape)==(3,4)'),('Returns a tensor','tf.is_tensor(linear_batch(tf.zeros((1,2)),tf.ones((2,1)),0))')])

lesson('tensorflow',2,'Record with GradientTape',
'TensorFlow records differentiable operations inside a GradientTape context. The tape then computes how a target depends on its sources.',
'with tf.GradientTape() as tape: ...',
'Trainable tf.Variable objects are watched automatically. Ordinary tensors must be explicitly watched with tape.watch. The forward computation must happen inside the context, and you should not convert intermediate values to NumPy.',
['Implement derivative(value) for x²+3x.','Create a floating-point tf.Variable and record the expression with GradientTape.','Return the gradient as a Python float.'],
'A None gradient often means the computation was outside the tape or detached.',
['x=tf.Variable(float(value)).','Compute loss inside the with block.','Return float(tape.gradient(loss,x).numpy()).'],
'''
import tensorflow as tf

def derivative(value):
    return None
''',
'''
import tensorflow as tf

def derivative(value):
    x=tf.Variable(float(value))
    with tf.GradientTape() as tape:
        loss=x*x+3*x
    return float(tape.gradient(loss,x).numpy())
''', [('Derivative at 2','abs(derivative(2)-7)<1e-6'),('Derivative at -3','abs(derivative(-3)+3)<1e-6'),('Derivative at zero','abs(derivative(0)-3)<1e-6')], ['Tape context','Forward expression','tape.gradient'])

lesson('tensorflow',3,'Compose a Keras model',
'Keras layers are reusable building blocks. A Sequential model expresses a straight path through layers, just like torch.nn.Sequential.',
'Input(2) → Dense(4, relu) → Dense(1)',
'Keras Dense stores a kernel shaped (inputs, outputs), whereas PyTorch Linear stores weight as (outputs, inputs). The mathematical operation is equivalent. An explicit Input builds the Keras model so parameter counts and output shapes are immediately available.',
['Implement make_model() with tf.keras.Sequential.','Use two input features, four hidden ReLU units, and one linear output.','Use an explicit tf.keras.Input(shape=(2,)).'],
'Do not add a sigmoid to a regression output unless the target requires it.',
['Use tf.keras.layers.Dense(4, activation="relu").','The output layer is Dense(1) without an activation.','Sequential accepts Input, hidden layer, output layer.'],
'''
import tensorflow as tf

def make_model():
    return None
''',
'''
import tensorflow as tf

def make_model():
    return tf.keras.Sequential([tf.keras.Input(shape=(2,)),tf.keras.layers.Dense(4,activation='relu'),tf.keras.layers.Dense(1)])
''', [('Correct batch output shape','tuple(make_model()(tf.ones((3,2))).shape)==(3,1)'),('Registers 17 scalar parameters','make_model().count_params()==17'),('Hidden layer uses ReLU','make_model().layers[0].activation.__name__=="relu"')], ['Input layer','Dense + ReLU','Dense output'])

lesson('tensorflow',4,'Build a tf.data pipeline',
'tf.data.Dataset describes a stream of examples and composable transformations. It keeps input pipelines separate from model code.',
'from_tensor_slices → batch → iterate',
'Here we keep order and retain the last partial batch. Larger jobs often add shuffle and prefetch. The order of transformations matters: batching before shuffling shuffles whole batches, not individual examples.',
['Implement make_dataset(x, y, batch_size).','Use tf.data.Dataset.from_tensor_slices((x,y)).','Batch without dropping the final partial batch.'],
'Prefetch overlaps input work with computation; it does not change the learning objective.',
['Create a dataset from the paired tensors.','Call .batch(batch_size, drop_remainder=False).','Return the resulting dataset.'],
'''
import tensorflow as tf

def make_dataset(x, y, batch_size):
    return None
''',
'''
import tensorflow as tf

def make_dataset(x, y, batch_size):
    return tf.data.Dataset.from_tensor_slices((x,y)).batch(batch_size,drop_remainder=False)
''', [('Three batches for five examples','len(list(make_dataset(tf.range(5),tf.range(5),2)))==3'),('Retains the last example','len(list(make_dataset(tf.range(5),tf.range(5),2))[-1][0])==1'),('Maintains paired labels','all(bool(tf.reduce_all(a*2==b)) for a,b in make_dataset(tf.range(5),tf.range(5)*2,2))')], ['Paired tensors','Dataset','Batches'])

lesson('tensorflow',5,'Apply gradients yourself',
'A custom TensorFlow training step gives you the same control as a PyTorch loop. Compute loss in a tape, request gradients, and pass them to an optimizer.',
'tape.gradient(loss, variables) → optimizer.apply_gradients',
'The optimizer expects pairs of (gradient, variable). Use the same variable objects involved in the forward pass. This scalar example makes the update easy to inspect before moving back to a full network.',
['Implement train_step(weight, optimizer, x, y).','Predict weight*x and compute mean squared error within a tape.','Apply the gradient and return the pre-update loss as a float.'],
'The tape records the calculation; the optimizer changes the variable.',
['Use tf.reduce_mean(tf.square(weight*x-y)).','grad=tape.gradient(loss,weight).','optimizer.apply_gradients([(grad,weight)]).'],
'''
import tensorflow as tf

def train_step(weight, optimizer, x, y):
    return None
''',
'''
import tensorflow as tf

def train_step(weight, optimizer, x, y):
    with tf.GradientTape() as tape:
        loss=tf.reduce_mean(tf.square(weight*x-y))
    grad=tape.gradient(loss,weight)
    optimizer.apply_gradients([(grad,weight)])
    return float(loss.numpy())
''', [('Returns loss before update','check_tf_step(train_step,"loss")'),('Applies the correct gradient','check_tf_step(train_step,"update")'),('Updates consistently on a second step','check_tf_step(train_step,"twice")')], ['Record loss','Compute gradient','Apply gradient'])

lesson('tensorflow',6,'Train with Keras',
'Keras can manage the training step for you after you compile a model with an optimizer and loss. Train the same line from the PyTorch capstone and compare the APIs.',
'build → compile → train_on_batch → predict',
'We use train_on_batch to keep the local exercise lightweight and make iteration explicit. model.fit is the higher-level interface for epochs over a dataset. Calling a model with training=False chooses inference behavior; this is different from changing the trainable flag.',
['Implement fit_model() returning a trained Keras model with one Dense(1) layer.','Compile with SGD(learning_rate=0.05) and MSE, then train 200 batches of the five examples.','Learn y=2x+1 for x=[-2,-1,0,1,2].'],
'The same problem is a useful API comparison, not evidence that one framework learns better.',
['Use tf.keras.Input(shape=(1,)) before Dense(1).','model.compile(optimizer=tf.keras.optimizers.SGD(.05),loss="mse").','Call model.train_on_batch(x,2*x+1) 200 times.'],
'''
import tensorflow as tf

def fit_model():
    tf.keras.utils.set_random_seed(7)
    model=tf.keras.Sequential([tf.keras.Input(shape=(1,)),tf.keras.layers.Dense(1)])
    # Compile and train the model.
    return model
''',
'''
import tensorflow as tf

def fit_model():
    tf.keras.utils.set_random_seed(7)
    model=tf.keras.Sequential([tf.keras.Input(shape=(1,)),tf.keras.layers.Dense(1)])
    model.compile(optimizer=tf.keras.optimizers.SGD(.05),loss='mse')
    x=tf.constant([[-2.],[-1.],[0.],[1.],[2.]])
    for _ in range(200):
        model.train_on_batch(x,2*x+1)
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

def public_curriculum():
    return {'courses':COURSES,'lessons':[{k:v for k,v in lesson.items() if k not in ('solution','checks')} | {'checkLabels':[c['label'] for c in lesson['checks']]} for lesson in LESSONS]}
