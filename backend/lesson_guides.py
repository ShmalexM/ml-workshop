"""Original small examples and orientation, taught before the independent tasks."""
from textwrap import dedent

ORIENTATION={
 'foundations':dict(welcome='Start with a function you can inspect. Machine learning means adjusting its numbers from examples, rather than choosing every number yourself.',goal='Explain a prediction, measure its error, then improve it one small step at a time.',prerequisites=[],terms=[['Model','A function that turns an input into a prediction.'],['Parameter','An adjustable number inside the model, such as weight or bias.'],['Training','Repeatedly changing parameters to reduce error on examples.']]),
 'pytorch':dict(welcome='You already know the prediction-and-error loop. PyTorch stores numbers in tensors and records the operations needed to calculate gradients.',goal='Build the same learning loop with tensors, automatic gradients and an optimizer.',prerequisites=['foundations'],terms=[['Tensor','A numbered array with a shape, data type and device.'],['Gradient','How much a small parameter change affects the loss.'],['Autograd','PyTorch’s automatic gradient calculation.']]),
 'tensorflow':dict(welcome='Reuse the ML ideas you learned earlier. TensorFlow has different names for many of the same building blocks; you do not need to master PyTorch first.',goal='Read tensor shapes, record gradients and train a small Keras model.',prerequisites=['foundations'],terms=[['Variable','A tensor whose value can be updated during training.'],['GradientTape','A context that records operations for differentiation.'],['Keras','A layer and training API used with TensorFlow here.']]),
 'modern':dict(welcome='An AI application is a pipeline of contracts: text becomes IDs, a model transforms them, and retrieval supplies evidence. Start with these pieces separately.',goal='Inspect tokenization, model shapes, structured prompts and retrieval without downloading a model.',prerequisites=['pytorch'],terms=[['Token','A text piece represented by an integer ID.'],['Checkpoint','Saved model parameters learned during training.'],['Retrieval','Selecting relevant source material for a query.']]),
 'cuda':dict(welcome='Start by assigning array positions to workers. A GPU launches many threads; each must know which data it owns and when its index is out of range.',goal='Reason about indexing and memory movement before writing small kernels.',prerequisites=['pytorch'],terms=[['Kernel','A function launched across GPU threads.'],['Block','A group of threads that can cooperate.'],['Global index','A thread’s position across the whole launch.']]),
 'harness':dict(welcome='An agent harness is the ordinary software around a model: it tracks state, validates tools and decides when a run stops. We will build those rules without an LLM.',goal='Make an agent’s allowed actions and stopping conditions explicit.',prerequisites=[],terms=[['State','A named phase of a run, such as running or waiting.'],['Tool contract','The allowed name, inputs and result for an operation.'],['Trace','A recorded sequence of what happened during a run.']]),
 'backend':dict(welcome='A backend receives inputs it does not control and must produce dependable behavior. Begin with a small data contract before thinking about a whole service.',goal='Handle invalid requests, repeated work, paging and readiness deliberately.',prerequisites=[],terms=[['Validation','Checking that input satisfies an explicit contract.'],['Idempotency','Repeated requests have the effect of a single accepted request.'],['Cursor','A stable position from which to continue a result list.']]),
 'web':dict(welcome='A web UI is easier to reason about when its state changes are small functions. We will practice those functions in JavaScript before tracing them through a browser app.',goal='Keep UI state predictable when actions, requests and saved data change.',prerequisites=[],terms=[['State','The data that determines what the UI displays.'],['Reducer','A function that maps previous state and an action to next state.'],['Immutable update','Creating a changed copy instead of modifying the original.']]),
 'rl':dict(welcome='In reinforcement learning, an agent chooses actions and learns from rewards. Begin with one environment step; training algorithms come after the interaction contract is clear.',goal='Trace an episode, accumulate rewards and handle its ending correctly.',prerequisites=['foundations'],terms=[['Observation','The information an environment gives the agent.'],['Reward','A numerical feedback signal after an action.'],['Episode','A sequence of interactions ending at a terminal state or rollout cutoff.']]),
 'data':dict(welcome='Before adding a language model, make your data pipeline inspectable. Track identity, break documents into useful pieces and measure which evidence a query retrieves.',goal='Build deterministic ingestion and retrieval behaviors on tiny inputs.',prerequisites=[],terms=[['Revision','A source-defined version of a record.'],['Chunk','A bounded piece of a larger document.'],['Recall','The fraction of expected relevant items that were retrieved.']]),
 'reliability':dict(welcome='Reliability starts with deciding what should happen when something fails. Use small, deterministic examples before adding clocks, networks or deployment tools.',goal='Bound retries, protect telemetry and justify a release with measurements.',prerequisites=['backend'],terms=[['Retry budget','A limit on how long or how often an operation may retry.'],['Desired state','The configuration a system is intended to reach.'],['Percentile','A value below which a specified proportion of measurements fall.']]),
 'interactive':dict(welcome='Interactive apps combine state, time and geometry. Model each separately before connecting them to a native UI or a game loop.',goal='Reason about lifecycle, movement, media fitting and replay-safe progress.',prerequisites=[],terms=[['Lifecycle','Transitions such as active, paused and stopped.'],['Delta time','Elapsed time since the previous update.'],['Aspect ratio','Width divided by height; keeping it fixed avoids stretching.']]),
}
GUIDES={}
def add(id,code,output,steps,question,choices,answer,feedback):
 GUIDES[id]=dict(code=dedent(code).strip()+'\n',output=output,steps=steps,question=question,choices=choices,answer=answer,feedback=feedback)

add('foundations-1','''
# A small model: a starting amount plus a per-item amount.
items = 3
weight = 2
bias = 1
prediction = weight * items + bias
print(prediction)
''','7',['Start with 3 items. The weight says to add 2 for each item.','Multiply 2 × 3 to get 6, then add the starting amount 1.'], 'If items becomes 4, keeping the same weight and bias, what is the prediction?', ['7','9','12'],1,'2 × 4 + 1 = 9. The challenge turns this same calculation into a reusable function.')
add('foundations-2','''
predictions = [3, 5]
targets = [1, 5]
squared_errors = [(p - y)**2 for p, y in zip(predictions, targets)]
print(squared_errors)
print(sum(squared_errors) / len(squared_errors))
''','[4, 0]\n2.0',['Subtract each correct target from its prediction, then square the difference.','Average the squared errors: (4 + 0) / 2.'], 'Why square the differences before averaging?', ['So positive and negative errors do not cancel','To make every error smaller','To turn targets into predictions'],0,'Squaring makes each error nonnegative. A prediction two units too low contributes the same squared error as two units too high.')
add('foundations-3','''
weight = 0.0
target = 3.0
rate = 0.1
gradient = 2 * (weight - target)
print(gradient)
print(round(weight - rate * gradient, 2))
''','-6.0\n0.6',['For the loss (weight − target)², the slope is 2 × (weight − target).','Subtracting a negative slope increases the weight toward the target.'], 'What happens if the learning rate is zero?', ['The weight jumps to 3','The weight remains 0','The gradient becomes positive'],1,'The update is weight − rate × gradient. A zero rate makes the update zero; it does not change the gradient.')
add('foundations-4','''
rows = list(range(10))
train = rows[:6]
validation = rows[6:8]
test = rows[8:]
print(len(train), len(validation), len(test))
''','6 2 2',['Use one partition to fit parameters and another to choose settings.','Keep the test partition for the final evaluation, after those choices.'], 'Which partition should stay out of parameter fitting?', ['Only training','Validation and test','None'],1,'Both validation and test stay out of parameter fitting. Validation informs choices; test should not become another tuning set.')
add('foundations-5','''
train = [2.0, 4.0, 6.0]
mean = sum(train) / len(train)
variance = sum((x - mean)**2 for x in train) / len(train)
scale = variance ** 0.5
print(round((6.0 - mean) / scale, 3))
''','1.225',['Compute the mean and population standard deviation from training data.','Subtract that mean and divide by that scale to normalize a value.'], 'How should a new test value be scaled?', ['Recalculate statistics using the test set','Use the training mean and scale','Always divide it by 100'],1,'Reusing training statistics avoids allowing evaluation data to influence preprocessing.')
add('foundations-6','''
weight = 0.0
for step in range(3):
    prediction = weight * 1.0
    error = prediction - 2.0
    gradient = 2 * error * 1.0
    weight -= 0.1 * gradient
    print(round(weight, 3))
''','0.4\n0.72\n0.976',['Predict with the current weight, then measure the difference from target 2.','Recompute the gradient after each update; the model has changed.'], 'Why recompute the prediction every step?', ['The updated parameters change the prediction','The target must change every step','The dataset must be downloaded again'],0,'The next gradient must describe the current model, not the model from before the last update.')
add('pytorch-1','''
import torch
x = torch.tensor([[1., 2.], [3., 4.]])
print(list(x.shape))
print((x + torch.tensor([10., 20.])).tolist())
''','[2, 2]\n[[11.0, 22.0], [13.0, 24.0]]',['Read shape [2, 2] as two rows and two columns.','The length-two vector is added to each row by broadcasting.'], 'What shape is the result?', ['[4]','[2, 2]','[2, 2, 2]'],1,'Broadcasting repeats the compatible vector conceptually. It does not add a new dimension here.')
add('pytorch-2','''
import torch
x = torch.tensor(3., requires_grad=True)
y = x * x
y.backward()
print(x.grad.item())
''','6.0',['requires_grad asks PyTorch to record how this value is used.','backward computes the derivative of x², which is 2x at x = 3.'], 'Where is the computed gradient stored?', ['x.grad','y.shape','x.device'],0,'The gradient for this leaf tensor accumulates in x.grad; it is separate from x’s numerical value.')
add('pytorch-3','''
import torch
layer = torch.nn.Linear(2, 1)
x = torch.zeros(3, 2)
print(list(layer(x).shape))
''','[3, 1]',['Linear(2, 1) maps two input features to one output for each example.','Three input rows produce three output rows.'], 'What does the first dimension, 3, represent?', ['Number of layers','Number of examples in the batch','Number of output features'],1,'Each row is one example. Changing the number of features is the layer’s job; the batch size stays the same.')
add('pytorch-4','''
import torch
from torch.utils.data import DataLoader
loader = DataLoader(torch.arange(5), batch_size=2, shuffle=False)
print([batch.tolist() for batch in loader])
''','[[0, 1], [2, 3], [4]]',['The loader groups five values into batches of at most two.','The final batch can be smaller when drop_last is not enabled.'], 'How many batches does this produce?', ['2','3','5'],1,'Two full batches consume four items; the fifth item forms the last batch.')
add('pytorch-5','''
import torch
w = torch.nn.Parameter(torch.tensor(0.))
optimizer = torch.optim.SGD([w], lr=0.1)
optimizer.zero_grad()
loss = (w - 2)**2
loss.backward()
optimizer.step()
print(round(w.item(), 1))
''','0.4',['Clear old gradients, compute the current loss, then call backward.','step applies the gradient update to the parameter.'], 'Why clear gradients before another independent step?', ['PyTorch accumulates gradients by default','The parameter must be reset to zero','SGD cannot handle negative gradients'],0,'Without clearing, a later backward call adds to the previous gradient. The parameter itself should keep its learned value.')
add('pytorch-6','''
import torch
model = torch.nn.Linear(1, 1)
model.eval()
with torch.no_grad():
    predictions = model(torch.tensor([[1.], [2.]]))
print(list(predictions.shape))
print(predictions.requires_grad)
''','[2, 1]\nFalse',['eval selects evaluation behavior for layers; it does not disable gradients.','no_grad avoids recording an autograd graph for this prediction.'], 'Which instruction disables gradient recording here?', ['model.eval()','torch.no_grad()','Linear(1, 1)'],1,'Evaluation mode and gradient recording are separate controls. The capstone uses both deliberately.')
add('tensorflow-1','''
import tensorflow as tf
x = tf.constant([[1., 2.], [3., 4.]])
print(x.shape.as_list())
print((x + tf.constant([10., 20.])).numpy().tolist())
''','[2, 2]\n[[11.0, 22.0], [13.0, 24.0]]',['A constant is a tensor; .shape tells you its dimensions.','A compatible length-two vector broadcasts across rows.'], 'Which part controls broadcasting compatibility?', ['The variable name','The dimensions','The import order'],1,'Broadcasting aligns dimensions from the right. Names and import order do not determine the result shape.')
add('tensorflow-2','''
import tensorflow as tf
x = tf.Variable(3.)
with tf.GradientTape() as tape:
    y = x * x
print(tape.gradient(y, x).numpy().item())
''','6.0',['The tape records the multiplication while its context is active.','Ask for the derivative of y with respect to x after recording.'], 'Where must y = x * x happen for this tape to record it?', ['Inside the tape context','Before creating the tape','Only after gradient()'],0,'A tape needs to observe the operations whose derivatives it will compute.')
add('tensorflow-3','''
import tensorflow as tf
model = tf.keras.Sequential([tf.keras.Input(shape=(2,)), tf.keras.layers.Dense(1)])
print(model(tf.zeros((3, 2))).shape.as_list())
''','[3, 1]',['The Input shape describes features in one example, excluding batch size.','Dense(1) gives each input row one output.'], 'What shape describes one example’s two input features?', ['(3, 2)','(2,)','(1,)'],1,'Input(shape=(2,)) leaves the batch dimension flexible.')
add('tensorflow-4','''
import tensorflow as tf
dataset = tf.data.Dataset.from_tensor_slices([0, 1, 2, 3, 4]).batch(2)
print([batch.numpy().tolist() for batch in dataset])
''','[[0, 1], [2, 3], [4]]',['from_tensor_slices creates an element for each value.','batch groups those elements while keeping the final partial batch.'], 'Does batch(2) discard the final item by default?', ['Yes','No','Only on a CPU'],1,'The final short batch remains unless drop_remainder=True is requested.')
add('tensorflow-5','''
import tensorflow as tf
w = tf.Variable(0.)
optimizer = tf.keras.optimizers.SGD(0.1)
with tf.GradientTape() as tape:
    loss = (w - 2)**2
gradient = tape.gradient(loss, w)
optimizer.apply_gradients([(gradient, w)])
print(round(float(w.numpy()), 1))
''','0.4',['Record the loss, then differentiate it with respect to the trainable variable.','Pass each gradient together with the variable it updates.'], 'What is the correct pair for apply_gradients?', ['(variable, loss)','(gradient, variable)','(learning_rate, loss)'],1,'The optimizer needs both the direction to move and the parameter to change.')
add('tensorflow-6','''
import tensorflow as tf
model = tf.keras.Sequential([tf.keras.Input(shape=(1,)), tf.keras.layers.Dense(1)])
model.compile(optimizer=tf.keras.optimizers.SGD(0.05), loss='mse')
print(model.loss)
print(model(tf.zeros((2, 1))).shape.as_list())
''','mse\n[2, 1]',['compile tells Keras how to measure error and update parameters.','Calling a compiled model still only computes predictions; training is a separate action.'], 'Does compile() by itself fit the model?', ['Yes','No','Only for Dense layers'],1,'Training requires data and an operation such as fit or train_on_batch. Compilation configures that operation.')
add('modern-1','''
vocabulary = {'[UNK]': 0, 'learn': 1, 'tensors': 2}
words = 'learn something'.split()
print([vocabulary.get(word, 0) for word in words])
''','[1, 0]',['First see tokenization as a plain dictionary lookup.','Unknown words use a known fallback; the challenge implements this with Hugging Face Tokenizers.'], 'What is the ID for an unseen word in this example?', ['1','0','Its character count'],1,'The defined unknown-token ID is zero. A real model needs its own matching tokenizer.')
add('modern-2','''
batch_size, tokens, hidden_size = 2, 3, 8
attention_heads = 2
print([batch_size, tokens, hidden_size])
print(hidden_size // attention_heads)
''','[2, 3, 8]\n4',['Track dimensions before instantiating a transformer: one hidden vector per token.','Split the hidden width evenly across attention heads. This example computes shape arithmetic, not model output.'], 'How many hidden vectors will this batch contain?', ['2','6','8'],1,'Two sequences with three tokens each produce six hidden vectors, each of width eight.')
add('modern-3','''
from langchain_core.prompts import ChatPromptTemplate
prompt = ChatPromptTemplate.from_messages([('human', 'Explain {topic}.')])
message = prompt.format_messages(topic='tensors')[0]
print(message.type)
print(message.content)
''','human\nExplain tensors.',['A template contains a named slot, topic.','Formatting produces a structured message; it does not call a model.'], 'What happened when the template was formatted?', ['An LLM generated an answer','A variable was substituted into a message','A model was trained'],1,'Prompt formatting is ordinary data transformation. The challenge adds a separate system message.')
add('modern-4','''
from langchain_core.runnables import RunnableLambda
strip = RunnableLambda(lambda text: text.strip())
length = RunnableLambda(len)
pipeline = strip | length
print(pipeline.invoke('  hi  '))
''','2',['The first runnable removes surrounding spaces.','The second receives the first result, so it counts two characters.'], 'What does the second runnable receive?', ['The original string with spaces','The string hi','The number 2'],1,'The pipe passes the previous runnable’s output into the next runnable’s input.')
add('modern-5','''
from llama_index.core.schema import Document
doc = Document(text='A tensor has a shape.', metadata={'source': 'example-notes'})
print(doc.text)
print(doc.metadata['source'])
''','A tensor has a shape.\nexample-notes',['Keep source text together with information about where it came from.','A Document is a data container here; creating one does not call an embedding model.'], 'Why keep the source metadata?', ['To replace the document text','To trace an answer back to its evidence','To guarantee the text is correct'],1,'Provenance lets you locate evidence. It does not guarantee that the source is accurate.')
add('modern-6','''
query = {'tensor', 'shape'}
document_words = {'a', 'tensor', 'has', 'a', 'shape'}
print(len(query & document_words))
''','2',['Use a transparent word-overlap score before introducing more complex ranking.','The intersection contains the shared words tensor and shape.'], 'Does a higher overlap score prove a document answers the question?', ['Yes, always','No, it is only a ranking signal','Only if the score is 2'],1,'A ranking score is not a correctness or grounding guarantee; inspect the retrieved evidence.')
add('cuda-1','''
threads_per_block = 4
block_id = 2
thread_id = 1
global_id = block_id * threads_per_block + thread_id
print(global_id)
''','9',['Blocks and threads are numbered from zero. Two complete blocks contain eight threads.','Add local thread 1 to that offset. This is launch arithmetic on the CPU.'], 'What global ID does block 2, thread 3 have?', ['5','11','12'],1,'2 × 4 + 3 = 11. This is the same indexing rule used in a one-dimensional kernel.')
add('cuda-2','''
size, threads_per_block = 5, 4
blocks = (size + threads_per_block - 1) // threads_per_block
valid = [i for i in range(blocks * threads_per_block) if i < size]
print(blocks)
print(valid)
''','2\n[0, 1, 2, 3, 4]',['Round the number of blocks up so all five items have a worker.','Eight workers are launched conceptually, but only five indices are valid.'], 'What should workers 5, 6 and 7 do?', ['Access the final item again','Skip the out-of-range work','Resize the array'],1,'A bounds guard prevents surplus threads from reading or writing outside the array.')
add('cuda-3','''
# Lists model separate host/device storage; no GPU transfer occurs here.
host = [1, 2]
device = host.copy()
device[0] = 9
print(host)
print(device.copy())
''','[1, 2]\n[9, 2]',['Separate copies help you reason about where the latest data lives.','The challenge replaces this mental model with explicit Numba transfer APIs.'], 'Which values are in the original host list?', ['[9, 2]','[1, 2]','[9, 9]'],1,'Changing a separate copy does not update the original. Copy results back when the host needs them.')
add('cuda-4','''
row, column, width = 1, 2, 4
flat_index = row * width + column
print(flat_index)
''','6',['In row-major order, each complete row occupies width positions.','Skip one row of four, then advance two columns.'], 'What is the flat index of row 2, column 0?', ['2','4','8'],2,'2 × 4 + 0 = 8. Check row and column bounds separately in a two-dimensional kernel.')
add('cuda-5','''
# CPU illustration of two workers combining a shared tile.
tile = [2, 3]
partial_sums = [value for value in tile]
print(sum(partial_sums))
''','5',['Each worker contributes a piece before anyone consumes the combined result.','Real shared-memory kernels need appropriate synchronization; this sequential example cannot demonstrate races.'], 'When may a worker safely read a tile another worker is filling?', ['Whenever it runs first','After the required block synchronization','Only after changing the block size'],1,'The needed writes must be visible before readers proceed. CPU simulation does not qualify real GPU race behavior.')
add('cuda-6','''
x, weight, bias = -3, 2, 1
linear = weight * x + bias
activated = max(0, linear)
print(linear, activated)
''','-5 0',['Compute an affine transform, then clamp negative values with ReLU.','A fused kernel can do both for one element before writing the result.'], 'Why might fusion help on a real GPU?', ['It can avoid an intermediate array write and read','It always changes the mathematical answer','It removes the need for a bounds guard'],0,'Avoiding intermediate memory traffic may help, but actual performance needs hardware measurement.')

add('harness-1',"state = 'idle'\nevent = 'start'\nnext_state = {('idle', 'start'): 'running'}[state, event]\nprint(next_state)",'running',['Treat state and event together as a lookup key.','The rule, rather than a model response, decides the next phase.'],'Does a transition table automatically allow every event?',['Yes','No, only declared pairs','Only for terminal states'],1,'The challenge rejects pairs that have no declared transition.')
add('harness-2',"required = {'id'}\nproposed = {'id': 3, 'shell': 'extra'}\nprint(set(proposed) == required)",'False',['Convert argument keys to a set to ignore ordering.','Exact-key validation rejects the extra shell field.'],'Is having every required key enough here?',['Yes','No, extra keys are also rejected','Only if the values are strings'],1,'This exercise uses an exact argument contract: no missing or extra keys.')
add('harness-3',"spent, next_cost, budget = 7, 3, 10\nprint(spent + next_cost <= budget)",'True',['Consider the cost of the proposed next step before running it.','Equality fits the budget; exceeding it does not.'],'Would a next cost of 4 fit?',['Yes','No','The spent amount does not matter'],1,'7 + 4 = 11, which exceeds the budget of 10.')
add('harness-4',"events = [{'type': 'tool', 'name': 'lookup', 'ok': True}, {'type': 'final', 'value': 7}]\nprint(events[-1]['type'])\nprint(events[-1]['value'])",'final\n7',['A trace separates tool activity from the final result.','Inspect both required successful actions and the final answer.'],'Does a correct final value alone prove the required tool ran?',['Yes','No','Only when it is a number'],1,'A behavioral evaluation checks the required evidence in the trace, not just the final string.')
add('backend-1',"raw_title = '  Train a model  '\ntitle = raw_title.strip()\nprint(title)\nprint(bool(title))",'Train a model\nTrue',['Normalize harmless formatting first.','Check that a meaningful value remains after normalization.'],'What happens to a title made only of spaces?',['It becomes an empty string','It becomes None','It stays valid'],0,'Trimming produces an empty string; the request validator must reject it.')
add('backend-2',"seen = {'request-1': {'result': 42}}\nprint(seen['request-1']['result'])",'42',['Use a stable request key to recognize work already accepted.','Returning the recorded result avoids applying the operation again.'],'Can the same key be reused with a different payload safely?',['Yes, silently overwrite','No, reject the conflict','Only when retried quickly'],1,'A key must identify the same request, not whichever payload arrives most recently.')
add('backend-3',"ids = [2, 7, 9, 12]\nafter = 7\nremaining = [id for id in ids if id > after]\nprint(remaining[:1])",'[9]',['A cursor names an ordering position rather than a page number.','Select IDs after that position, then apply the page size.'],'Should ID 7 appear again after cursor 7?',['Yes','No','Only on page 2'],1,'The cursor comparison is strict so the last item from the prior page is not repeated.')
add('backend-4',"required_health = [True, False]\nprint(all(required_health))",'False',['A process can be alive while a required dependency is unhealthy.','Readiness is false when any required dependency cannot serve work.'],'Should an optional dependency always block readiness?',['Yes','No','Only on Mondays'],1,'The challenge distinguishes required dependencies from optional degraded capabilities.')
add('web-1',"const before = {count: 1, label: 'runs'};\nconst after = {...before, count: before.count + 2};\nconsole.log(before.count, after.count);",'1 3',['Object spread creates a new object containing the previous fields.','Overriding count on the copy leaves the original count unchanged.'],'What is before.count after the update?',['1','3','undefined'],0,'The original object remains unchanged. The reducer challenge packages this update behind an action.')
add('web-2',"const currentRequest = 3;\nconst responseRequest = 2;\nconsole.log(currentRequest === responseRequest);",'false',['Each request receives an identity.','An old response must not replace the currently requested result.'],'What should happen to this response?',['Apply it because it arrived last','Ignore it because its ID is stale','Reset the whole UI'],1,'Arrival order is not request order; the current request ID determines which result may update state.')
add('web-3',"const source = ['GPU notes', 'API notes'];\nconst query = ' gpu '.trim().toLowerCase();\nconsole.log(JSON.stringify(source.filter(title => title.toLowerCase().includes(query))));",'["GPU notes"]',['Normalize both the query and the candidate text for a case-insensitive comparison.','filter returns a new array, leaving source intact.'],'What remains in source?',['Only GPU notes','Both original titles','Nothing'],1,'Filtering creates a derived view. It does not remove items from the canonical collection.')
add('web-4',"const saved = JSON.parse('{\"version\":1,\"darkMode\":true}');\nconst theme = saved.darkMode ? 'dark' : 'light';\nconsole.log(theme);",'dark',['Parse stored text to recover data.','Translate the old boolean field into the new theme value.'],'What can JSON.parse do with malformed text?',['Always return null','Throw an exception','Repair any missing brace'],1,'The challenge adds try/catch, version checks and defaults around this happy-path migration.')
add('rl-1',"position, action = 1, 1\nnext_position = max(0, min(4, position + action))\nprint(next_position)",'2',['Treat the action as movement before considering rewards.','Clamping keeps the observation inside the corridor’s valid positions.'],'What happens when position 0 receives action -1?',['Position becomes -1','Position stays 0','Position jumps to 4'],1,'The lower boundary is zero. The full environment also returns reward and ending signals.')
add('rl-2',"rewards = [1, 2]\ngamma = 0.5\nprint(rewards[0] + gamma * rewards[1])",'2.0',['Keep the immediate reward at full value.','Discount the next reward before adding it.'],'With gamma = 0, what is this return?',['1','2','3'],0,'A zero discount ignores future rewards and keeps only the immediate reward.')
add('rl-3',"values = [1, 5, 2]\nprint(values.index(max(values)))",'1',['The values list contains one estimate per available action.','The greedy action is the index of the largest value, not the value itself.'],'What does epsilon-greedy add to this rule?',['Occasional exploration','A bigger action space','Guaranteed optimal behavior'],0,'With probability epsilon, the policy explores an available action instead of using the current best estimate.')
add('rl-4',"reward, next_value, gamma = 1, 4, 0.5\nterminated = True\ntarget = reward if terminated else reward + gamma * next_value\nprint(target)",'1',['A true terminal transition has no future task rewards to estimate.','An external rollout cutoff is different; the underlying task may continue.'],'What target would a nonterminal truncated transition use here?',['1','3','4'],1,'Bootstrap the continuing task: 1 + 0.5 × 4 = 3. Truncation alone does not make the future value zero.')
add('data-1',"old = {'id': 'a', 'revision': 1}\nnew = {'id': 'a', 'revision': 3}\nchosen = new if new['revision'] > old['revision'] else old\nprint(chosen['revision'])",'3',['Stable identity says these are versions of the same record.','Compare revisions to decide which version to retain.'],'If revisions tie, what policy does the challenge use?',['Keep the first seen','Always duplicate both','Pick randomly'],0,'A defined tie rule makes repeated processing deterministic.')
add('data-2',"tokens = ['a', 'b', 'c', 'd', 'e']\nsize, overlap = 3, 1\nprint(tokens[:size])\nprint(tokens[size-overlap:size-overlap+size])","['a', 'b', 'c']\n['c', 'd', 'e']",['The first window starts at zero and contains three tokens.','Advance by size minus overlap: two positions, preserving c at the boundary.'],'What overlap would stop a size-3 window from advancing?',['0','1','3'],2,'Overlap equal to size creates a zero stride. Reject it rather than entering a nonprogressing loop.')
add('data-3',"graph = {'a': ['b'], 'b': ['a', 'c']}\nseen = {'a', 'b'}\nnext_nodes = set(graph['b']) - seen\nprint(sorted(next_nodes))","['c']",['A seen set records nodes already visited.','Subtracting it from neighbors prevents revisiting the cycle back to a.'],'Why also set a depth limit?',['To bound the neighborhood being requested','To make node IDs shorter','To remove all cycles from the graph'],0,'A seen set prevents repeats; the depth limit controls how far the query is allowed to explore.')
add('data-4',"ranked = ['a', 'x', 'b']\nrelevant = {'a', 'b'}\nhits = set(ranked[:2]) & relevant\nprint(len(hits) / len(relevant))",'0.5',['Take the first two ranked positions, then count unique relevant hits.','One of two expected relevant documents is present.'],'What is recall at 3 for the same list?',['0.5','1.0','3.0'],1,'Both expected relevant IDs are in the top three, so recall is 2 / 2.')
add('reliability-1',"base, cap = 2, 5\nprint([min(cap, base * 2**n) for n in range(4)])",'[2, 4, 5, 5]',['Double each delay until the per-delay cap is reached.','The full challenge also stops when total waiting would exceed a budget.'],'Would the first three delays fit a total budget of 10?',['Yes','No','The cap makes the sum irrelevant'],1,'2 + 4 + 5 = 11. Each delay can fit the cap while their sum exceeds the total budget.')
add('reliability-2',"event = {'user': 'demo', 'token': 'example-only'}\nsafe = {key: '[REDACTED]' if key == 'token' else value for key, value in event.items()}\nprint(safe['token'])",'[REDACTED]',['A structured event exposes field names that can be checked explicitly.','Replace sensitive values in a new mapping; the challenge also walks nested containers.'],'Would checking only top-level keys handle nested tokens?',['Yes','No','Only if JSON is used'],1,'A token can appear in a nested dictionary or list. Recursive traversal handles those locations.')
add('reliability-3',"current = {'api': 'v1'}\ndesired = {'api': 'v2', 'worker': 'v1'}\nprint(sorted(set(desired) - set(current)))\nprint([key for key in current if key in desired and current[key] != desired[key]])","['worker']\n['api']",['Set differences identify resources to create.','For shared keys, compare values to identify updates; this only plans changes.'],'Does computing this diff deploy anything?',['Yes','No','Only the new resource'],1,'A plan is data. Applying it is a separate operation that needs its own controls and verification.')
add('reliability-4',"import math\nlatencies = [10, 20, 30, 40]\nindex = math.ceil(0.95 * len(latencies)) - 1\nprint(sorted(latencies)[index])",'40',['Nearest-rank p95 selects a position in the sorted observations.','For four samples, that position is the last one; a tiny sample is not a stable operational estimate.'],'Can successful latency alone reveal a high failure rate?',['Yes','No','Only at p95'],1,'A release gate must inspect both success rate and the latency distribution used by its policy.')
add('interactive-1',"state = 'active'\nevent = 'background'\nprint({('active', 'background'): 'paused'}[state, event])",'paused',['Name the lifecycle states explicitly.','Use an event to determine the transition rather than scattering flags through the UI.'],'Which event should resume a paused app in this model?',['close','resume','background'],1,'A resume transition returns to active; closing moves to stopped.')
add('interactive-2',"position, velocity = 10.0, 4.0\ndelta_time, max_delta = 0.5, 0.1\nprint(position + velocity * min(delta_time, max_delta))",'10.4',['Velocity is distance per unit time, so multiply it by elapsed time.','Cap an unusually long pause before applying movement.'],'Why cap delta time after a long pause?',['To avoid an oversized jump','To make movement depend on frame count','To change the units of velocity'],0,'The cap limits one update’s movement. It is a deliberate behavior choice, not a substitute for measuring elapsed time.')
add('interactive-3',"width, height = 800, 400\nbox_width, box_height = 300, 300\nscale = min(box_width / width, box_height / height)\nprint(width * scale, height * scale)",'300.0 150.0',['Compute how much each axis could be scaled to fit the box.','Use the smaller factor for both dimensions to preserve the aspect ratio.'],'Should the image be stretched to 300 × 300 for a fit?', ['Yes','No','Only for PNGs'],1,'A fit preserves the original shape and leaves unused space. Cropping and stretching are different operations.')
add('interactive-4',"events = [{'id': 'a', 'points': 5}, {'id': 'a', 'points': 5}]\nseen = set()\ntotal = 0\nfor event in events:\n    if event['id'] not in seen:\n        seen.add(event['id'])\n        total += event['points']\nprint(total)",'5',['Use the event ID to recognize a repeated delivery.','Only the first accepted event contributes points.'],'How many points should another replay of event a add?',['5','0','10'],1,'A replay carries an already accepted identity. It must not award the same progress twice.')
