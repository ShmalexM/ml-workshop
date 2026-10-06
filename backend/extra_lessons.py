"""Offline framework and CUDA lessons."""
from textwrap import dedent
COURSES_EXTRA=[dict(id='modern',title='Modern AI stack',subtitle='Hugging Face, LangChain and LlamaIndex',icon='layers',color='purple'),dict(id='cuda',title='CUDA & GPU programming',subtitle='Real kernel logic in a CPU simulator',icon='cpu',color='orange')]
LESSONS_EXTRA=[]
def add(course,n,title,intro,concept,explanation,tasks,tip,hints,starter,solution,checks,diagram,reference):
 LESSONS_EXTRA.append(dict(id=f'{course}-{n}',course=course,title=title,minutes=18 if n==6 else 14,xp=150 if n==6 else 100,intro=intro,concept=concept,explanation=explanation,tasks=tasks,tip=tip,hints=hints,starter=dedent(starter).strip()+'\n',solution=dedent(solution).strip()+'\n',checks=[dict(label=a,expr=b) for a,b in checks],diagram=diagram,reference=dict(title=reference[0],url=reference[1])))
add('modern',1,'Build a local tokenizer',('A language model reads integer IDs. A tokenizer splits text into pieces called tokens '
 'and gives each token an ID, the same way every time. Build a word-level tokenizer with '
 'Hugging Face tokenizers.'),'text → tokens → integer IDs',('With vocabulary ["learn", "tensors"], assign IDs 1 and 2. Keep ID 0 for the unknown '
 'token [UNK], so "learn something" becomes [1, 0]. The Whitespace pre-tokenizer splits at '
 'spaces and also separates punctuation. For example, "learn!" becomes two tokens: "learn" '
 'and "!".'),['Build a vocabulary with [UNK] at ID 0 and words at IDs 1, 2, and so on.',
 'Create a WordLevel tokenizer and set its pre_tokenizer to Whitespace().',
 'Return the tokenizer from make_tokenizer(words). The words are unique and exclude [UNK].'],'Try text containing a word absent from words. Its ID should be 0.',['Create a vocabulary dict that maps "[UNK]" to 0.','Construct WordLevel(vocab=..., unk_token="[UNK]").','Set tokenizer.pre_tokenizer = Whitespace().'],'''
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

def make_tokenizer(words):
    # Return the tokenizer.
    return None

print(make_tokenizer(["learn", "tensors"]))
''','''
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

def make_tokenizer(words):
    vocab = {'[UNK]': 0}
    for i, word in enumerate(words, start=1):
        vocab[word] = i
    tokenizer = Tokenizer(WordLevel(vocab=vocab, unk_token='[UNK]'))
    tokenizer.pre_tokenizer = Whitespace()
    return tokenizer
''',[('Preserves vocabulary IDs',"make_tokenizer(['learn','tensors']).encode('learn tensors').ids==[1,2]"),('Maps unknown words to zero',"make_tokenizer(['learn']).encode('learn unseen').ids==[1,0]"),('Empty text has no tokens',"make_tokenizer(['learn']).encode('').ids==[]")],['Text','Word pieces','IDs'],('Hugging Face Tokenizers','https://huggingface.co/docs/tokenizers/quicktour'))
add('modern',2,'Inspect an untrained transformer',('A transformer turns each token ID into a vector of numbers, then updates those vectors '
 'using attention to mix information between tokens. A configuration sets the sizes. '
 'Building from a config creates an untrained model with random weights.'),'[batch, tokens] → transformer → [batch, tokens, hidden]',('For two sequences of three tokens, hidden size 8 gives an output shape of (2, 3, 8). '
 'Each token has eight numbers, called its hidden state. Two attention heads split that '
 'width into groups of four. One layer performs one round of these updates, using '
 'intermediate size 16 inside its feed-forward network.'),['Create BertConfig with vocab_size=16, hidden_size=8, num_hidden_layers=1, '
 'num_attention_heads=2, and intermediate_size=16.',
 'Pass the config to BertModel. Use the local constructor.',
 'Call model.eval() and return model from make_model().'],'The hidden size must divide evenly by the number of attention heads: 8 / 2 = 4.',['Create the configuration before the model.',
 'Pass the five sizes from the task as named BertConfig arguments, then call '
 'BertModel(config).',
 'Set model.eval() before returning model.'],'''
import torch
from transformers import BertConfig, BertModel

def make_model():
    # Return the untrained model in evaluation mode.
    return None

print(make_model())
''','''
import torch
from transformers import BertConfig, BertModel

def make_model():
    config = BertConfig(
        vocab_size=16,
        hidden_size=8,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=16,
    )
    model = BertModel(config)
    model.eval()
    return model
''',[('Produces hidden states per token',
  'tuple(make_model()(input_ids=torch.tensor([[1,2,3]])).last_hidden_state.shape)==(1,3,8)'),
 ('Supports a batch of sequences',
  'tuple(make_model()(input_ids=torch.tensor([[1,2],[3,4]])).last_hidden_state.shape)==(2,2,8)'),
 ('Evaluation mode is enabled', 'not make_model().training'),
 ('Uses vocab_size 16 and the requested architecture',
  '(lambda config: (config.vocab_size, config.hidden_size, config.num_hidden_layers, '
  'config.num_attention_heads, config.intermediate_size) == (16, 8, 1, 2, '
  '16))(make_model().config)')],['Token IDs','Random transformer','Hidden states'],('Hugging Face BERT','https://huggingface.co/docs/transformers/model_doc/bert'))
add('modern',3,'Make a structured prompt',('A chat prompt is a list of messages with roles. A system message gives behavior '
 'instructions, and a human message holds the request. A template fills named slots while '
 'preserving those roles.'),'variables → ChatPromptTemplate → messages',('If the human template is "Explain {topic} with one example." and topic is "loss", '
 'formatting produces "Explain loss with one example." The system message stays the same. '
 'Keeping the two messages separate lets you inspect both the instruction and the request '
 'before sending them.'),['Build a ChatPromptTemplate with system text "You are a concise ML tutor.".',
 'Add human text "Explain {topic} with one example.".',
 'Return prompt.format_messages(topic=topic) from build_messages(topic).'],('Inspect each message’s type and content. A correct sentence with the wrong role is still '
 'the wrong message.'),['ChatPromptTemplate.from_messages accepts a list of (role, text) pairs.',
 'Use a system pair followed by a human pair containing the {topic} slot.',
 'Call prompt.format_messages(topic=topic) to return the message list.'],'''
from langchain_core.prompts import ChatPromptTemplate

def build_messages(topic):
    # Return the formatted message list.
    return None

print(build_messages("loss"))
''','''
from langchain_core.prompts import ChatPromptTemplate

def build_messages(topic):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a concise ML tutor."),
        ("human", "Explain {topic} with one example."),
    ])
    return prompt.format_messages(topic=topic)
''',[('Preserves the system role',"build_messages('loss')[0].type=='system'"),('Substitutes the topic',"build_messages('loss')[1].content=='Explain loss with one example.'"),('Does not hardcode one topic',"build_messages('autograd')[1].content=='Explain autograd with one example.'"),('Preserves the human role',"build_messages('tensors')[1].type=='human'")],['Topic','Template','Chat messages'],('LangChain prompt templates','https://reference.langchain.com/python/langchain-core/prompts/'))
add('modern',4,'Compose a runnable pipeline',('In LangChain, a runnable is a step with invoke() for one input and batch() for a list. '
 'The pipe operator chains runnables by passing one step’s output to the next.'),'normalize | tokenize | count',('For " Learn ML now ", stripping spaces and lowercasing gives "learn ml now". Splitting '
 'produces ["learn", "ml", "now"], and counting gives 3. Each step has one job. The same '
 'chain can process several strings with batch().'),['Wrap lowercase-and-strip, whitespace splitting, and word counting in RunnableLambda '
 'objects.',
 'Chain the three runnables in that order.',
 'Return the chain from make_pipeline(), supporting invoke(text) and batch(list_of_texts).'],'Use split() without an argument so repeated spaces and an empty string behave correctly.',['Start with a runnable that returns text.strip().lower().',
 'Make the next runnable return text.split(), then count with RunnableLambda(len).',
 'Return normalize | split | count.'],'''
from langchain_core.runnables import RunnableLambda

def make_pipeline():
    # Return the chained runnable.
    return None

print(make_pipeline())
''','''
from langchain_core.runnables import RunnableLambda

def make_pipeline():
    normalize = RunnableLambda(lambda text: text.strip().lower())
    split = RunnableLambda(lambda text: text.split())
    count = RunnableLambda(len)
    return normalize | split | count
''',[('Counts tokens',"make_pipeline().invoke(' Learn ML now ')==3"),('Empty input produces zero',"make_pipeline().invoke('   ')==0"),('Supports batching',"make_pipeline().batch(['one','two words',''])==[1,2,0]")],['Normalize','Split','Count'],('LangChain runnables','https://reference.langchain.com/python/langchain-core/runnables/'))
add('modern',5,'Give documents structure',('Search results need a way to identify each piece of text and its source. A LlamaIndex '
 'TextNode stores a text chunk, an ID, and metadata such as its source name.'),'document → nodes + metadata → retrieval',('Two paragraphs from "notes" get IDs "notes:0" and "notes:1". The second node keeps its '
 'paragraph text and metadata {"source": "notes", "index": 1}. A search result can use '
 'that ID and metadata to point back to the right paragraph.'),['Create one TextNode for each paragraph, preserving its text.',
 'Set metadata to {"source": source, "index": i} and id_ to f"{source}:{i}".',
 'Return the list from make_nodes(paragraphs, source), using indices starting at 0.'],'Use enumerate(paragraphs) so duplicate paragraph text still gets a different ID.',['Create an empty list and loop over enumerate(paragraphs).',
 'Build each TextNode with text, metadata, and id_.',
 'Append TextNode(text=paragraph, metadata={"source": source, "index": i}, '
 'id_=f"{source}:{i}") and return the list.'],'''
from llama_index.core.schema import TextNode

def make_nodes(paragraphs, source):
    # Return a list of TextNode objects.
    return None

print(make_nodes(["A tensor has a shape.", "Loss measures error."], "notes"))
''','''
from llama_index.core.schema import TextNode

def make_nodes(paragraphs, source):
    nodes = []
    for i, paragraph in enumerate(paragraphs):
        node = TextNode(
            text=paragraph,
            metadata={"source": source, "index": i},
            id_=f"{source}:{i}",
        )
        nodes.append(node)
    return nodes
''',[('Preserves paragraph content',"[n.text for n in make_nodes(['A','B'],'notes')]==['A','B']"),('Preserves source metadata',"make_nodes(['A'],'book')[0].metadata=={'source':'book','index':0}"),('Provides stable IDs',"make_nodes(['A','B'],'notes')[1].node_id=='notes:1'"),('Handles no paragraphs',"make_nodes([],'notes')==[]")],['Paragraphs','TextNode','Source metadata'],('LlamaIndex nodes','https://developers.llamaindex.ai/python/framework/module_guides/loading/documents_and_nodes/'))
add('modern',6,'Rank text by word overlap',('A retriever selects text that may help answer a query. Lexical search compares words '
 'directly. Here each shared word adds one point to a node’s score.'),'query terms ∩ node terms → score → top k',('For query "tensor shape", a node containing "tensor" scores 1 and "a tensor has a shape" '
 'scores 2. Converting words to sets counts repeated words once. Sort higher scores first, '
 'then use the node ID to order ties. Return both the node and its score so the ranking '
 'can be inspected.'),['Count distinct shared words after lowercasing and splitting the query and each node’s '
 'text.',
 'Omit nodes with score 0. Wrap positive matches in NodeWithScore.',
 'Return at most k results sorted by descending score, then ascending node_id. Return [] '
 'when k <= 0.'],('Try query "TENSOR tensor". Its two spellings become one set member and should score only '
 'once.'),['Make sets from query.lower().split() and node.text.lower().split().','Count the intersection and wrap positive scores with NodeWithScore(node=node, score=score).','Sort with key=lambda r: (-r.score, r.node.node_id), then keep the first k.'],'''
from llama_index.core.schema import TextNode, NodeWithScore

def retrieve(query, nodes, k=2):
    # Return a ranked list of NodeWithScore objects.
    return None

print(retrieve("tensor shape", [TextNode(text="A tensor has a shape", id_="notes:0")]))
''','''
from llama_index.core.schema import TextNode, NodeWithScore

def retrieve(query, nodes, k=2):
    if k <= 0:
        return []
    terms = set(query.lower().split())
    results = []
    for node in nodes:
        score = len(terms & set(node.text.lower().split()))
        if score:
            results.append(NodeWithScore(node=node, score=float(score)))
    return sorted(results, key=lambda r: (-r.score, r.node.node_id))[:k]
''',[('Ranks by distinct overlap',
  "retrieve('tensor loss',[TextNode(text='loss',id_='a'),TextNode(text='tensor "
  "loss',id_='b')])[0].node.node_id=='b'"),
 ('Counts a repeated query word once',
  "retrieve('TENSOR tensor',[TextNode(text='tensor',id_='a')])[0].score==1"),
 ('Returns no unmatched nodes',
  "retrieve('cuda',[TextNode(text='tokenizer',id_='a')])==[]"),
 ('Handles zero requested results',
  "retrieve('cuda',[TextNode(text='cuda',id_='a')],0)==[]"),
 ('Breaks ties deterministically',
  '[r.node.node_id for r in '
  "retrieve('x',[TextNode(text='x',id_='b'),TextNode(text='x',id_='a')])]==['a','b']")],['Query words', 'Rank nodes', 'Matching text'],('LlamaIndex NodeWithScore','https://developers.llamaindex.ai/python/framework-api-reference/schema/'))
cuda_ref=('NVIDIA: CUDA Python kernels','https://nvidia.github.io/numba-cuda/user/kernels.html')
add('cuda',1,'Meet blocks and threads',('A CUDA kernel describes what one thread does. A launch creates blocks of threads that '
 'run that function. Each thread uses its position to choose an array element.'),'global_index = block_index × block_size + thread_index',('With four threads per block, block 2 starts at index 8. Thread 1 in that block has '
 'global index 2 × 4 + 1 = 9. cuda.grid(1) computes that index. The launch syntax is '
 'kernel[blocks, threads_per_block](arguments). Threads can run in any order, so each '
 'writes its own element.'),['Find the global index inside fill_indices(out).',
 'Write that index to the matching output element.',
 'Use the supplied run_indices wrapper for sizes 4, 8, 12, or 16. Each launch has exactly '
 'one thread per element.'],'Using threadIdx.x alone repeats 0 through 3 in each block. Include the block offset.',['Each block starts after all threads in earlier blocks.',
 'Use i = cuda.grid(1) to include that offset.',
 'Write out[i] = i.'],'''
import numpy as np
from numba import cuda

@cuda.jit
def fill_indices(out):
    # Write the result into the output array.
    pass

def run_indices(n):
    out = np.full(n, -1, dtype=np.int32)
    fill_indices[n // 4, 4](out)
    return out

print(run_indices(8))
''','''
import numpy as np
from numba import cuda

@cuda.jit
def fill_indices(out):
    i = cuda.grid(1)
    out[i] = i

def run_indices(n):
    out = np.full(n, -1, dtype=np.int32)
    fill_indices[n // 4, 4](out)
    return out

print(run_indices(8))
''',[('Indexes across two blocks',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    out = cuda.to_device(np.full(8, -1, dtype=np.int32))\\n    fill_indices[2, '
  "4](out)\\n    return np.array_equal(out.copy_to_host(), np.arange(8))\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))'),
 ('Indexes across four blocks',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    out = cuda.to_device(np.full(16, -1, dtype=np.int32))\\n    fill_indices[4, '
  "4](out)\\n    return np.array_equal(out.copy_to_host(), np.arange(16))\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))'),
 ('Single block works',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    out = cuda.to_device(np.full(4, -1, dtype=np.int32))\\n    fill_indices[1, '
  "4](out)\\n    return np.array_equal(out.copy_to_host(), np.arange(4))\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))')],['Grid','Blocks','Threads'],cuda_ref)
add('cuda',2,'Guard the edge of the grid',('Array lengths often do not divide evenly by block size. Round the block count up so '
 'every element gets a thread, then skip threads beyond the array’s end.'),'blocks = (n + threads − 1) // threads',('Five elements with four threads per block need two blocks. That launches indices 0 '
 'through 7, but only 0 through 4 belong to the arrays. A guard around both reads and the '
 'write prevents indices 5 through 7 from touching memory.'),['Find the global index in add_kernel(a, b, out).',
 'Add the matching input elements only when the index is within out.size. All three arrays '
 'have equal lengths.',
 'Keep the wrapper’s rounded-up launch. It should handle partial final blocks and empty '
 'arrays.'],'Check i < out.size before reading or writing the arrays.',['Compute i = cuda.grid(1).','Put both reads and the write inside the bounds guard.','Use if i < out.size: out[i] = a[i] + b[i].'],'''
import numpy as np
from numba import cuda

@cuda.jit
def add_kernel(a, b, out):
    # Write the result into the output array.
    pass

def add_vectors(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    out = np.zeros_like(a)
    if a.size:
        threads = 4
        blocks = (a.size + threads - 1) // threads
        add_kernel[blocks, threads](a, b, out)
    return out

print(add_vectors([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]))
''','''
import numpy as np
from numba import cuda

@cuda.jit
def add_kernel(a, b, out):
    i = cuda.grid(1)
    if i < out.size:
        out[i] = a[i] + b[i]

def add_vectors(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    out = np.zeros_like(a)
    if a.size:
        threads = 4
        blocks = (a.size + threads - 1) // threads
        add_kernel[blocks, threads](a, b, out)
    return out
''',[('Adds five elements with three spare threads',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    a = cuda.to_device(np.asarray([1, 2, 3, 4, 5], dtype=np.float32))\\n    b = '
  'cuda.to_device(np.asarray([5, 4, 3, 2, 1], dtype=np.float32))\\n    out = '
  'cuda.to_device(np.full(5, np.nan, dtype=np.float32))\\n    add_kernel[2, 4](a, b, '
  "out)\\n    return np.allclose(out.copy_to_host(), [6] * 5)\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))'),
 ('Guards a single element',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    a = cuda.to_device(np.asarray([2], dtype=np.float32))\\n    b = '
  'cuda.to_device(np.asarray([-3], dtype=np.float32))\\n    out = '
  'cuda.to_device(np.full(1, np.nan, dtype=np.float32))\\n    add_kernel[1, 4](a, b, '
  "out)\\n    return np.allclose(out.copy_to_host(), [-1])\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))'),
 ('Handles signed values in a partial block',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    a = cuda.to_device(np.asarray([-2, 0, 3], dtype=np.float32))\\n    b = '
  'cuda.to_device(np.asarray([1, -4, 2], dtype=np.float32))\\n    out = '
  'cuda.to_device(np.full(3, np.nan, dtype=np.float32))\\n    add_kernel[1, 4](a, b, '
  "out)\\n    return np.allclose(out.copy_to_host(), [-1, -4, 5])\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))'),
 ('Empty wrapper input and a working kernel',
  "add_vectors([], []).shape == (0,) and (lambda scope: (exec('def _check():\\n    import "
  'numpy as np\\n    from numba import cuda\\n    a = cuda.to_device(np.asarray([1], '
  'dtype=np.float32))\\n    b = cuda.to_device(np.asarray([2], dtype=np.float32))\\n    '
  'out = cuda.to_device(np.full(1, np.nan, dtype=np.float32))\\n    add_kernel[1, 4](a, b, '
  "out)\\n    return np.allclose(out.copy_to_host(), [3])\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))')],['Round up grid','Guard bounds','Write valid values'],cuda_ref)
add('cuda',3,'Move data explicitly',('The CPU is the host and the GPU is the device. Their arrays live in separate memory. '
 'Copy the input to the device, run the kernel, and copy the result back to the host.'),'to_device → launch → copy_to_host',('Starting with host values [1, 2], cuda.to_device creates a separate device array. '
 'Doubling that device array gives [2, 4], while the host input stays [1, 2]. copy_to_host '
 'returns the changed values. Earlier wrappers passed NumPy arrays directly, letting Numba '
 'make the copies for each launch.'),['In doubled(values), convert values to a float32 host array and copy it with '
 'cuda.to_device.',
 'Launch double_kernel on that device array with four threads per block when the array is '
 'nonempty.',
 'Return a new host NumPy array using copy_to_host, leaving the original unchanged. Handle '
 'empty input.'],'Pass device to the kernel. Passing host would let Numba copy back into the input array.',['Set host = np.asarray(values, dtype=np.float32).',
 'Set device = cuda.to_device(host). For nonempty input, compute the rounded-up block '
 'count and launch on device.',
 'Return device.copy_to_host().'],'''
import numpy as np
from numba import cuda

@cuda.jit
def double_kernel(data):
    i = cuda.grid(1)
    if i < data.size:
        data[i] *= 2

def doubled(values):
    # Return a new host array containing the doubled values.
    return None

print(doubled([1, 2]))
''','''
import numpy as np
from numba import cuda

@cuda.jit
def double_kernel(data):
    i = cuda.grid(1)
    if i < data.size:
        data[i] *= 2

def doubled(values):
    host = np.asarray(values, dtype=np.float32)
    device = cuda.to_device(host)
    if host.size:
        threads = 4
        blocks = (host.size + threads - 1) // threads
        double_kernel[blocks, threads](device)
    return device.copy_to_host()
''',[('Kernel doubles a check-owned device array',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    device = cuda.to_device(np.array([-2, 0.5, 3], dtype=np.float32))\\n    '
  'double_kernel[1, 4](device)\\n    return np.allclose(device.copy_to_host(), [-4, 1, '
  '6])\\n\', scope), scope["_check"]())[-1])(dict(globals()))'),
 ('Wrapper passes a device array to the kernel',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    namespace = "
  'doubled.__globals__\\n    original = namespace["double_kernel"]\\n    launches = '
  '[]\\n    class DeviceLaunch:\\n        def __getitem__(self, grid):\\n            def '
  'launch(device):\\n                assert hasattr(device, "copy_to_host"), "Pass the '
  'device array to the kernel"\\n                assert grid == (2, 4), "Use four threads '
  'per block and round up"\\n                launches.append(device)\\n                '
  'original[grid](device)\\n            return launch\\n    try:\\n        '
  'namespace["double_kernel"] = DeviceLaunch()\\n        result = doubled([1, 2, 3, 4, '
  '5])\\n        return len(launches) == 1 and isinstance(result, np.ndarray) and '
  'result.dtype == np.float32 and np.allclose(result, [2, 4, 6, 8, 10])\\n    '
  'finally:\\n        namespace["double_kernel"] = original\\n\', scope), '
  'scope["_check"]())[-1])(dict(globals()))'),
 ('Doubles values and leaves host input unchanged',
  '(lambda host: (lambda result: isinstance(result, np.ndarray) and result is not host and '
  'np.array_equal(result, [2, 4]) and np.array_equal(host, [1, '
  '2]))(doubled(host)))(np.array([1, 2], dtype=np.float32))'),
 ('Returns host arrays for empty and nonempty inputs',
  'isinstance(doubled([1]), np.ndarray) and np.array_equal(doubled([1]), [2]) and '
  'doubled([]).shape == (0,)')],['Host array','Device array','Host result'],cuda_ref)
add('cuda',4,'Index a two-dimensional kernel',('A matrix has row and column coordinates. cuda.grid(2) gives each thread a pair of '
 'indices, so it can work on one matrix element.'),'out[col, row] = source[row, col]',('Transposing swaps rows and columns. A 2-by-3 input needs a 3-by-2 output. The value at '
 'source[1, 0] goes to out[0, 1]. Check each coordinate against its own input dimension '
 'before reading the value.'),['Get row and col from cuda.grid(2) inside transpose_kernel(source, out).',
 'Skip threads whose row or column is outside source.shape.',
 'Write the source value to the output position with its coordinates swapped.'],'A square matrix can conceal a swapped-axis bug. Always test a rectangle.',['The output’s first coordinate is the input’s column.',
 'Check row < source.shape[0] and col < source.shape[1].',
 'Inside the guard, write out[col, row] = source[row, col].'],'''
import numpy as np
from numba import cuda

@cuda.jit
def transpose_kernel(source, out):
    # Write the result into the output array.
    pass

def transpose(values):
    source = np.asarray(values, dtype=np.float32)
    out = np.zeros((source.shape[1], source.shape[0]), dtype=np.float32)
    blocks = ((source.shape[0] + 1) // 2, (source.shape[1] + 1) // 2)
    transpose_kernel[blocks, (2, 2)](source, out)
    return out

print(transpose([[1, 2, 3], [4, 5, 6]]))
''','''
import numpy as np
from numba import cuda

@cuda.jit
def transpose_kernel(source, out):
    row, col = cuda.grid(2)
    if row < source.shape[0] and col < source.shape[1]:
        out[col, row] = source[row, col]

def transpose(values):
    source = np.asarray(values, dtype=np.float32)
    out = np.zeros((source.shape[1], source.shape[0]), dtype=np.float32)
    blocks = ((source.shape[0] + 1) // 2, (source.shape[1] + 1) // 2)
    transpose_kernel[blocks, (2, 2)](source, out)
    return out
''',[('Transposes a rectangle',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    source = cuda.to_device(np.asarray([[1, 2, 3], [4, 5, 6]], '
  'dtype=np.float32))\\n    out = cuda.to_device(np.full((3, 2), np.nan, '
  'dtype=np.float32))\\n    transpose_kernel[(1, 2), (2, 2)](source, out)\\n    return '
  "np.allclose(out.copy_to_host(), [[1, 4], [2, 5], [3, 6]])\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))'),
 ('Guards both axes for one element',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    source = cuda.to_device(np.asarray([[9]], dtype=np.float32))\\n    out = '
  'cuda.to_device(np.full((1, 1), np.nan, dtype=np.float32))\\n    transpose_kernel[(1, '
  "1), (2, 2)](source, out)\\n    return np.allclose(out.copy_to_host(), [[9]])\\n', "
  'scope), scope["_check"]())[-1])(dict(globals()))'),
 ('Handles partial blocks on both axes',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    source = cuda.to_device(np.asarray(np.arange(15).reshape(3, 5), '
  'dtype=np.float32))\\n    out = cuda.to_device(np.full((5, 3), np.nan, '
  'dtype=np.float32))\\n    transpose_kernel[(2, 3), (2, 2)](source, out)\\n    return '
  "np.allclose(out.copy_to_host(), np.arange(15).reshape(3, 5).T)\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))')],['2D launch','Guard both axes','Transpose'],cuda_ref)
add('cuda',5,'Cooperate with shared memory',('Threads in one block can share an array. A barrier makes every thread wait until the '
 'others reach the same point. Use it after writing shared values and before reading '
 'another thread’s value.'),'load shared values → barrier → reduce → write',('For input [1, 2, 3] and a block of eight threads, the shared array becomes [1, 2, 3, 0, '
 '0, 0, 0, 0]. Every thread reaches the barrier. Then thread 0 adds the slots and writes '
 '6. Reading before the writes finish is a race: the result depends on which thread runs '
 'first.'),['Create eight shared float32 slots in block_sum_kernel(values, out).',
 'Each thread writes its input value or zero when out of bounds, then reaches '
 'cuda.syncthreads().',
 'Thread 0 sums the eight slots and writes the result at the block index.'],('Keep cuda.syncthreads() outside the bounds guard so the threads that write padding also '
 'reach it.'),['Create shared = cuda.shared.array(8, dtype=float32).','Each thread fills shared[cuda.threadIdx.x], then call cuda.syncthreads().','Only thread 0 loops over the eight shared values and writes out[cuda.blockIdx.x].'],'''
import numpy as np
from numba import cuda, float32

@cuda.jit
def block_sum_kernel(values, out):
    # Write the result into the output array.
    pass

def block_sums(values):
    values = np.asarray(values, dtype=np.float32)
    blocks = (values.size + 7) // 8
    out = np.zeros(blocks, dtype=np.float32)
    if blocks:
        block_sum_kernel[blocks, 8](values, out)
    return out

print(block_sums([1, 2, 3]))
''','''
import numpy as np
from numba import cuda, float32

@cuda.jit
def block_sum_kernel(values, out):
    shared = cuda.shared.array(8, dtype=float32)
    tid = cuda.threadIdx.x
    i = cuda.grid(1)
    shared[tid] = values[i] if i < values.size else 0
    cuda.syncthreads()
    if tid == 0:
        total = 0.0
        for j in range(8):
            total += shared[j]
        out[cuda.blockIdx.x] = total

def block_sums(values):
    values = np.asarray(values, dtype=np.float32)
    blocks = (values.size + 7) // 8
    out = np.zeros(blocks, dtype=np.float32)
    if blocks:
        block_sum_kernel[blocks, 8](values, out)
    return out
''',[('Sums a full block',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    values = cuda.to_device(np.asarray(np.arange(8), dtype=np.float32))\\n    '
  'out = cuda.to_device(np.full(1, np.nan, dtype=np.float32))\\n    block_sum_kernel[1, '
  "8](values, out)\\n    return np.allclose(out.copy_to_host(), [28])\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))'),
 ('Zero-pads the last block',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    values = cuda.to_device(np.asarray(np.arange(11), dtype=np.float32))\\n    '
  'out = cuda.to_device(np.full(2, np.nan, dtype=np.float32))\\n    block_sum_kernel[2, '
  "8](values, out)\\n    return np.allclose(out.copy_to_host(), [28, 27])\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))'),
 ('Sums signed values',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    values = cuda.to_device(np.asarray([-1, -2, -3], dtype=np.float32))\\n    '
  'out = cuda.to_device(np.full(1, np.nan, dtype=np.float32))\\n    block_sum_kernel[1, '
  "8](values, out)\\n    return np.allclose(out.copy_to_host(), [-6])\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))'),
 ('All eight threads use shared memory and reach a barrier',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    import "
  'threading\\n    from numba import cuda\\n    from numba.cuda.simulator.kernelapi import '
  'FakeCUDAShared, FakeCUDAModule\\n    from unittest.mock import patch\\n    allocations, '
  'barriers = set(), set()\\n    shared_array = FakeCUDAShared.array\\n    syncthreads = '
  'FakeCUDAModule.syncthreads\\n    def record_array(self, shape, dtype):\\n        '
  'allocations.add(threading.current_thread())\\n        return shared_array(self, shape, '
  'dtype)\\n    def record_barrier(self):\\n        '
  'barriers.add(threading.current_thread())\\n        return syncthreads(self)\\n    '
  'values = cuda.to_device(np.arange(8, dtype=np.float32))\\n    out = '
  'cuda.to_device(np.full(1, np.nan, dtype=np.float32))\\n    with '
  'patch.object(FakeCUDAShared, "array", record_array), patch.object(FakeCUDAModule, '
  '"syncthreads", record_barrier):\\n        block_sum_kernel[1, 8](values, out)\\n    '
  'return len(allocations) == 8 and len(barriers) == 8 and np.allclose(out.copy_to_host(), '
  '[28])\\n\', scope), scope["_check"]())[-1])(dict(globals()))'),
 ('Empty wrapper input and a working block kernel',
  "block_sums([]).shape == (0,) and (lambda scope: (exec('def _check():\\n    import numpy "
  'as np\\n    from numba import cuda\\n    values = cuda.to_device(np.asarray([2, 3], '
  'dtype=np.float32))\\n    out = cuda.to_device(np.full(1, np.nan, '
  'dtype=np.float32))\\n    block_sum_kernel[1, 8](values, out)\\n    return '
  "np.allclose(out.copy_to_host(), [5])\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))')],['Shared memory','Block barrier','Block result'],cuda_ref)
add('cuda',6,'Fuse an ML operation',('Compute scale × a + b, then ReLU, which clamps values below zero to zero. Doing both '
 'steps in one kernel is called fusion: it avoids storing the intermediate array between '
 'steps.'),'out[i] = max(scale × a[i] + b[i], 0)',('For a = −3, b = 1, and scale = 2, the first step gives −5 and ReLU gives 0. For a = 3 '
 'with the same settings, the result is 7. Each thread performs both calculations for one '
 'index, then writes only the final value.'),['Find the global index in fused_kernel(a, b, scale, out), and guard it against out.size.',
 'Compute scale * a[i] + b[i] and clamp negative values to zero.',
 'Write the result to out[i]. Use the supplied wrapper to inspect signed inputs and a '
 'partial final block.'],('Try a negative scale as well as a negative input. Clamp after computing scale * a[i] + '
 'b[i].'),['Use i = cuda.grid(1), then check i < out.size.','Compute value = scale * a[i] + b[i].','Set out[i] = value if value > 0 else 0.'],'''
import numpy as np
from numba import cuda

@cuda.jit
def fused_kernel(a, b, scale, out):
    # Write the result into the output array.
    pass

def fused(a, b, scale):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    if a.size == 0:
        return np.empty(0, dtype=np.float32)
    da = cuda.to_device(a)
    db = cuda.to_device(b)
    out = cuda.device_array(a.shape, dtype=np.float32)
    threads = 4
    blocks = (a.size + threads - 1) // threads
    fused_kernel[blocks, threads](da, db, scale, out)
    return out.copy_to_host()

print(fused([-3, 3], [1, 1], 2))
''','''
import numpy as np
from numba import cuda

@cuda.jit
def fused_kernel(a, b, scale, out):
    i = cuda.grid(1)
    if i < out.size:
        value = scale * a[i] + b[i]
        out[i] = value if value > 0 else 0

def fused(a, b, scale):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    if a.size == 0:
        return np.empty(0, dtype=np.float32)
    da = cuda.to_device(a)
    db = cuda.to_device(b)
    out = cuda.device_array(a.shape, dtype=np.float32)
    threads = 4
    blocks = (a.size + threads - 1) // threads
    fused_kernel[blocks, threads](da, db, scale, out)
    return out.copy_to_host()
''',[('Scales, adds, then applies ReLU',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    a = cuda.to_device(np.array([-2, 0, 3], dtype=np.float32))\\n    b = '
  'cuda.to_device(np.array([1, -1, 2], dtype=np.float32))\\n    out = '
  'cuda.to_device(np.full(3, np.nan, dtype=np.float32))\\n    fused_kernel[1, 4](a, b, 2, '
  "out)\\n    return np.allclose(out.copy_to_host(), [0, 0, 8])\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))'),
 ('Negative scale and partial block',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    a = cuda.to_device(np.array([1, 2, 3, 4, 5], dtype=np.float32))\\n    b = '
  'cuda.to_device(np.array([5, 4, 3, 2, 1], dtype=np.float32))\\n    out = '
  'cuda.to_device(np.full(5, np.nan, dtype=np.float32))\\n    fused_kernel[2, 4](a, b, '
  "-0.5, out)\\n    return np.allclose(out.copy_to_host(), [4.5, 3, 1.5, 0, 0])\\n', "
  'scope), scope["_check"]())[-1])(dict(globals()))'),
 ('Zero scale keeps a positive bias',
  "(lambda scope: (exec('def _check():\\n    import numpy as np\\n    from numba import "
  'cuda\\n    a = cuda.to_device(np.array([7], dtype=np.float32))\\n    b = '
  'cuda.to_device(np.array([2], dtype=np.float32))\\n    out = cuda.to_device(np.full(1, '
  'np.nan, dtype=np.float32))\\n    fused_kernel[1, 4](a, b, 0, out)\\n    return '
  "np.allclose(out.copy_to_host(), [2])\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))'),
 ('Empty wrapper input and a working fused kernel',
  "fused([], [], 1).shape == (0,) and (lambda scope: (exec('def _check():\\n    import "
  'numpy as np\\n    from numba import cuda\\n    a = cuda.to_device(np.array([-2, 0, 3], '
  'dtype=np.float32))\\n    b = cuda.to_device(np.array([1, -1, 2], '
  'dtype=np.float32))\\n    out = cuda.to_device(np.full(3, np.nan, '
  'dtype=np.float32))\\n    fused_kernel[1, 4](a, b, 2, out)\\n    return '
  "np.allclose(out.copy_to_host(), [0, 0, 8])\\n', scope), "
  'scope["_check"]())[-1])(dict(globals()))')],['Copy inputs','Fused kernel','Validate output'],cuda_ref)
