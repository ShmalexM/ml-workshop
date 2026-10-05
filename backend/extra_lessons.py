"""Original local framework and CUDA curriculum, reviewed against Claude guidance."""
from textwrap import dedent
COURSES_EXTRA=[dict(id='modern',title='Modern AI stack',subtitle='Hugging Face, LangChain and LlamaIndex',icon='layers',color='purple'),dict(id='cuda',title='CUDA & GPU programming',subtitle='Real kernel logic in a CPU simulator',icon='cpu',color='orange')]
LESSONS_EXTRA=[]
def add(course,n,title,intro,concept,explanation,tasks,tip,hints,starter,solution,checks,diagram,reference):
 LESSONS_EXTRA.append(dict(id=f'{course}-{n}',course=course,title=title,minutes=18 if n==6 else 14,xp=150 if n==6 else 100,intro=intro,concept=concept,explanation=explanation,tasks=tasks,tip=tip,hints=hints,starter=dedent(starter).strip()+'\n',solution=dedent(solution).strip()+'\n',checks=[dict(label=a,expr=b) for a,b in checks],diagram=diagram,reference=dict(title=reference[0],url=reference[1])))
add('modern',1,'Build a local tokenizer','Models process token IDs, not raw strings. A tokenizer supplies a repeatable mapping from text fragments to integers.\n\nBuild a tiny vocabulary locally using Hugging Face Tokenizers. This is a word-level teaching tokenizer, not a pretrained production tokenizer.','text → tokens → integer IDs','Unknown words need a defined fallback. Here [UNK] is assigned ID 0. Whitespace splitting makes the example transparent. Real pretrained models require the exact tokenizer and vocabulary used during training; arbitrary token IDs cannot be substituted.',['Implement make_tokenizer(words).','Use Tokenizer, WordLevel and Whitespace with [UNK] at index 0 and words in order starting at 1.','Return the tokenizer; the provided vocabulary contains unique words other than [UNK].'],'A tokenizer is part of a model’s input contract.',['Create a vocabulary dict with [UNK]:0.','Construct WordLevel(vocab=..., unk_token="[UNK]").','Set tokenizer.pre_tokenizer=Whitespace().'],'''
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

def make_tokenizer(words):
    return None
''','''
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

def make_tokenizer(words):
    vocab={'[UNK]':0,**{word:i+1 for i,word in enumerate(words)}}
    tokenizer=Tokenizer(WordLevel(vocab=vocab,unk_token='[UNK]'))
    tokenizer.pre_tokenizer=Whitespace()
    return tokenizer
''',[('Preserves vocabulary IDs',"make_tokenizer(['learn','tensors']).encode('learn tensors').ids==[1,2]"),('Maps unknown words to zero',"make_tokenizer(['learn']).encode('learn unseen').ids==[1,0]"),('Empty text has no tokens',"make_tokenizer(['learn']).encode('').ids==[]")],['Text','Word pieces','IDs'],('Hugging Face Tokenizers','https://huggingface.co/docs/tokenizers/quicktour'))
add('modern',2,'Inspect an untrained transformer','A transformer configuration specifies architecture. Constructing a model from a config initializes random weights; loading a trained checkpoint is a different operation.','[batch, tokens] → transformer → [batch, tokens, hidden]','Use a tiny BERT configuration with vocabulary 16, hidden size 8, one layer, two attention heads, and intermediate size 16. This model is deliberately untrained. Its output shape is meaningful; its predictions are not useful language understanding.',['Implement make_model() with BertConfig and BertModel.','Use vocab_size=16, hidden_size=8, num_hidden_layers=1, num_attention_heads=2, intermediate_size=16.','Return the model in eval mode. Do not download weights.'],'Attention head count must divide the hidden size.',['Construct the small config first.','Use BertModel(config), not from_pretrained.','Call model.eval() before returning it.'],'''
import torch
from transformers import BertConfig, BertModel

def make_model():
    return None
''','''
import torch
from transformers import BertConfig, BertModel

def make_model():
    model=BertModel(BertConfig(vocab_size=16,hidden_size=8,num_hidden_layers=1,num_attention_heads=2,intermediate_size=16))
    model.eval()
    return model
''',[('Produces hidden states per token',"tuple(make_model()(input_ids=torch.tensor([[1,2,3]])).last_hidden_state.shape)==(1,3,8)"),('Supports a batch of sequences',"tuple(make_model()(input_ids=torch.tensor([[1,2],[3,4]])).last_hidden_state.shape)==(2,2,8)"),('Evaluation mode is enabled',"not make_model().training"),('Vocabulary is local and tiny',"make_model().config.vocab_size==16")],['Token IDs','Random transformer','Hidden states'],('Hugging Face BERT','https://huggingface.co/docs/transformers/model_doc/bert'))
add('modern',3,'Make a structured prompt','LangChain prompt templates make variable substitution explicit and preserve chat roles. You can inspect and test prompts without calling an LLM.','variables → ChatPromptTemplate → messages','A chat prompt is structured data: a system message carries guidance, and a human message carries the task. This lesson formats messages only. No model response is generated, and templating by itself does not make untrusted input safe.',['Implement build_messages(topic).','Use ChatPromptTemplate with system text "You are a concise ML tutor." and human text "Explain {topic} with one example.".','Return the formatted list of messages.'],'Test prompt inputs and roles as carefully as any other interface.',['Import ChatPromptTemplate from langchain_core.prompts.','Use from_messages with ("system",...) and ("human",...).','Call format_messages(topic=topic).'],'''
from langchain_core.prompts import ChatPromptTemplate

def build_messages(topic):
    return None
''','''
from langchain_core.prompts import ChatPromptTemplate

def build_messages(topic):
    prompt=ChatPromptTemplate.from_messages([('system','You are a concise ML tutor.'),('human','Explain {topic} with one example.')])
    return prompt.format_messages(topic=topic)
''',[('Preserves the system role',"build_messages('loss')[0].type=='system'"),('Substitutes the topic',"build_messages('loss')[1].content=='Explain loss with one example.'"),('Does not hardcode one topic',"build_messages('autograd')[1].content=='Explain autograd with one example.'"),('Preserves the human role',"build_messages('tensors')[1].type=='human'")],['Topic','Template','Chat messages'],('LangChain prompt templates','https://reference.langchain.com/python/langchain-core/prompts/'))
add('modern',4,'Compose a runnable pipeline','LangChain runnables share invoke and batch interfaces. Compose ordinary Python transformations first to learn the orchestration model without an external model.','normalize | tokenize | count','The pipe operator composes outputs into inputs. Here the pipeline strips surrounding whitespace, lowercases text, splits on whitespace and counts words. This is deterministic preprocessing, not an LLM or agent.',['Implement make_pipeline() using RunnableLambda objects.','Compose lowercase-and-strip, whitespace splitting and token counting.','Return a runnable that supports invoke(text) and batch(list_of_texts).'],'Make each stage’s input and output types clear.',['RunnableLambda wraps a Python callable.','str.split() handles repeated spaces and empty input.','Return normalize | split | count.'],'''
from langchain_core.runnables import RunnableLambda

def make_pipeline():
    return None
''','''
from langchain_core.runnables import RunnableLambda

def make_pipeline():
    normalize=RunnableLambda(lambda text:text.strip().lower())
    split=RunnableLambda(lambda text:text.split())
    count=RunnableLambda(lambda words:len(words))
    return normalize | split | count
''',[('Counts tokens',"make_pipeline().invoke(' Learn ML now ')==3"),('Empty input produces zero',"make_pipeline().invoke('   ')==0"),('Supports batching',"make_pipeline().batch(['one','two words',''])==[1,2,0]")],['Normalize','Split','Count'],('LangChain runnables','https://reference.langchain.com/python/langchain-core/runnables/'))
add('modern',5,'Give documents structure','LlamaIndex nodes are chunks of content with metadata and stable identifiers. Those details make retrieved evidence traceable to its source.','document → nodes + metadata → retrieval','Build TextNode objects from small paragraphs. Preserve the source and each paragraph’s index. Downstream retrieval can then return both text and provenance. No embedding model is needed to learn this representation.',['Implement make_nodes(paragraphs, source).','Create a TextNode per paragraph with metadata {source: source, index: i}.','Give each node id_ equal to f"{source}:{i}" and return the list.'],'Good retrieval results need provenance, not just matching text.',['Import TextNode from llama_index.core.schema.','Pass text, metadata and id_ to each TextNode.','Use enumerate(paragraphs) for stable indices.'],'''
from llama_index.core.schema import TextNode

def make_nodes(paragraphs, source):
    return None
''','''
from llama_index.core.schema import TextNode

def make_nodes(paragraphs, source):
    return [TextNode(text=p,metadata={'source':source,'index':i},id_=f'{source}:{i}') for i,p in enumerate(paragraphs)]
''',[('Preserves paragraph content',"[n.text for n in make_nodes(['A','B'],'notes')]==['A','B']"),('Preserves source metadata',"make_nodes(['A'],'book')[0].metadata=={'source':'book','index':0}"),('Provides stable IDs',"make_nodes(['A','B'],'notes')[1].node_id=='notes:1'"),('Handles no paragraphs',"make_nodes([],'notes')==[]")],['Paragraphs','TextNode','Source metadata'],('LlamaIndex nodes','https://developers.llamaindex.ai/python/framework/module_guides/loading/documents_and_nodes/'))
add('modern',6,'Retrieve evidence with scores','Retrieval selects relevant pieces of content before answer generation. Build an explicit lexical retriever that returns LlamaIndex NodeWithScore objects.','query terms ∩ node terms → score → top k','Count distinct shared lowercase whitespace-separated terms. Discard zero matches, sort by descending score and then ascending node ID for ties, and return the first k. This transparent baseline does not perform semantic vector search and does not generate an answer.',['Implement retrieve(query, nodes, k=2).','Score each node by the number of distinct overlapping lowercase words; omit zero matches.','Return NodeWithScore objects sorted by score descending, then node_id ascending; k<=0 returns [].'],'Evaluate retrieval separately from generated answers: was the supporting evidence found?',['Make sets from query.lower().split() and node.text.lower().split().','Count the intersection and wrap positive scores with NodeWithScore(node=node,score=score).','Sort by (-result.score,result.node.node_id), then slice.'],'''
from llama_index.core.schema import TextNode, NodeWithScore

def retrieve(query, nodes, k=2):
    return None
''','''
from llama_index.core.schema import TextNode, NodeWithScore

def retrieve(query, nodes, k=2):
    if k<=0:return []
    terms=set(query.lower().split())
    results=[]
    for node in nodes:
        score=len(terms & set(node.text.lower().split()))
        if score:results.append(NodeWithScore(node=node,score=float(score)))
    return sorted(results,key=lambda r:(-r.score,r.node.node_id))[:k]
''',[('Ranks by distinct overlap',"retrieve('tensor loss',[TextNode(text='loss',id_='a'),TextNode(text='tensor loss',id_='b')])[0].node.node_id=='b'"),('Preserves numeric relevance',"retrieve('TENSOR tensor',[TextNode(text='tensor',id_='a')])[0].score==1"),('Returns no irrelevant evidence',"retrieve('cuda',[TextNode(text='tokenizer',id_='a')])==[]"),('Handles zero requested results',"retrieve('cuda',[TextNode(text='cuda',id_='a')],0)==[]"),('Breaks ties deterministically',"[r.node.node_id for r in retrieve('x',[TextNode(text='x',id_='b'),TextNode(text='x',id_='a')])]==['a','b']")],['Query','Rank nodes','Return evidence'],('LlamaIndex NodeWithScore','https://developers.llamaindex.ai/python/framework-api-reference/schema/'))
cuda_ref=('NVIDIA: CUDA Python kernels','https://nvidia.github.io/numba-cuda/user/kernels.html')
add('cuda',1,'Meet blocks and threads','A CUDA kernel describes what one thread does. A launch creates a grid of blocks, each containing threads that execute that code.\n\nThis Mac runs the kernel through a CPU simulator, not an NVIDIA GPU.','global_index = block_index × block_size + thread_index','In a 1D launch, cuda.grid(1) computes the global thread index. Four blocks of four threads cover sixteen positions. Thread execution order is not a contract: write independent output elements using explicit indices. CUDA C++ spells the index blockIdx.x * blockDim.x + threadIdx.x.',['Implement fill_indices(out) as a CUDA kernel.','Each thread writes its global index into the corresponding output element.','The supplied wrapper launches exactly n threads for n=4,8,12,16.'],'A kernel does not return the result array; it writes into an output buffer.',['Use cuda.grid(1) or the explicit block/thread formula.','Write out[i] = i.','Do not loop over the whole array in every thread.'],'''
import numpy as np
from numba import cuda

@cuda.jit
def fill_indices(out):
    pass  # Write this thread's index.

def run_indices(n):
    out=np.full(n,-1,dtype=np.int32)
    fill_indices[n//4,4](out)
    return out

print(run_indices(8))
''','''
import numpy as np
from numba import cuda

@cuda.jit
def fill_indices(out):
    i=cuda.grid(1)
    out[i]=i

def run_indices(n):
    out=np.full(n,-1,dtype=np.int32)
    fill_indices[n//4,4](out)
    return out

print(run_indices(8))
''',[('Indexes across two blocks','np.array_equal(run_indices(8),np.arange(8))'),('Indexes across four blocks','np.array_equal(run_indices(16),np.arange(16))'),('Single block works','np.array_equal(run_indices(4),np.arange(4))')],['Grid','Blocks','Threads'],cuda_ref)
add('cuda',2,'Guard the edge of the grid','Real array lengths rarely divide evenly by block size. Round the block count up, then guard any threads beyond the array boundary.','blocks = (n + threads − 1) // threads','The final block may contain more threads than remaining elements. Accessing out-of-bounds memory is a bug; a simulator may raise an exception, but real hardware failure behavior differs. Guard accesses to both input and output. This exercise assumes equally sized arrays.',['Complete add_kernel(a,b,out).','Compute the global index and add a[i]+b[i] only when i is in bounds.','Use the provided wrapper to test partial final blocks and empty arrays.'],'Check i < out.size before reading or writing the arrays.',['Compute i=cuda.grid(1).','Put both reads and the write inside the bounds guard.','If i<out.size: out[i]=a[i]+b[i].'],'''
import numpy as np
from numba import cuda

@cuda.jit
def add_kernel(a,b,out):
    pass

def add_vectors(a,b):
    a=np.asarray(a,dtype=np.float32)
    b=np.asarray(b,dtype=np.float32)
    out=np.zeros_like(a)
    if a.size:add_kernel[(a.size+3)//4,4](a,b,out)
    return out
''','''
import numpy as np
from numba import cuda

@cuda.jit
def add_kernel(a,b,out):
    i=cuda.grid(1)
    if i<out.size:out[i]=a[i]+b[i]

def add_vectors(a,b):
    a=np.asarray(a,dtype=np.float32)
    b=np.asarray(b,dtype=np.float32)
    out=np.zeros_like(a)
    if a.size:add_kernel[(a.size+3)//4,4](a,b,out)
    return out
''',[('Partial final block','np.allclose(add_vectors([1,2,3,4,5],[5,4,3,2,1]),[6]*5)'),('One element','np.allclose(add_vectors([2],[-3]),[-1])'),('Empty arrays','add_vectors([],[]).shape==(0,)')],['Round up grid','Guard bounds','Write valid values'],cuda_ref)
add('cuda',3,'Move data explicitly','GPU arrays live in a separate device memory space. Copy inputs to the device, launch a kernel, then copy the result back to the host.\n\nHere those operations are simulated in CPU memory; their API semantics are still useful to practice.','to_device → launch → copy_to_host','Implicit transfers can hide expensive movement in real applications. Keep intermediates on the GPU and transfer only when needed. This exercise returns a new host array and leaves the original unchanged. Actual transfer timing needs real NVIDIA hardware.',['Implement doubled(values).','Convert to float32, copy with cuda.to_device, and run the provided in-place double kernel using four threads per block.','Return a host NumPy array with copy_to_host; handle empty input.'],'Use separate host/device variables to make ownership visible.',['host=np.asarray(values,dtype=np.float32).','device=cuda.to_device(host); launch on device if size>0.','Return device.copy_to_host().'],'''
import numpy as np
from numba import cuda

@cuda.jit
def double_kernel(data):
    i=cuda.grid(1)
    if i<data.size:data[i]*=2

def doubled(values):
    return None
''','''
import numpy as np
from numba import cuda

@cuda.jit
def double_kernel(data):
    i=cuda.grid(1)
    if i<data.size:data[i]*=2

def doubled(values):
    host=np.asarray(values,dtype=np.float32)
    device=cuda.to_device(host)
    if host.size:double_kernel[(host.size+3)//4,4](device)
    return device.copy_to_host()
''',[('Doubles signed values','np.allclose(doubled([-2,.5,3]),[-4,1,6])'),('Returns a host array','isinstance(doubled([1]),np.ndarray)'),('Keeps host input unchanged','(lambda a: (doubled(a) is not a) and np.array_equal(a,[1,2]))(np.array([1,2],dtype=np.float32))'),('Handles empty arrays','doubled([]).shape==(0,)')],['Host array','Device array','Host result'],cuda_ref)
add('cuda',4,'Index a two-dimensional kernel','Images and matrices benefit from 2D thread indexing. cuda.grid(2) supplies two coordinates; you decide what those coordinates mean for your data.','out[column, row] = input[row, column]','Transpose swaps axes, so a (2,3) input needs a (3,2) output. Bound each coordinate independently. The straightforward kernel here teaches correctness; efficient transposes on real hardware often use shared memory and careful access patterns.',['Complete transpose_kernel(source,out).','Use row,col=cuda.grid(2) and guard against source.shape.','Write out[col,row]=source[row,col].'],'A square matrix can conceal a swapped-axis bug. Always test a rectangle.',['cuda.grid(2) returns a pair of indices.','Check row<source.shape[0] and col<source.shape[1].','The output coordinates are reversed.'],'''
import numpy as np
from numba import cuda

@cuda.jit
def transpose_kernel(source,out):
    pass

def transpose(values):
    source=np.asarray(values,dtype=np.float32)
    out=np.zeros((source.shape[1],source.shape[0]),dtype=np.float32)
    blocks=((source.shape[0]+1)//2,(source.shape[1]+1)//2)
    transpose_kernel[blocks,(2,2)](source,out)
    return out
''','''
import numpy as np
from numba import cuda

@cuda.jit
def transpose_kernel(source,out):
    row,col=cuda.grid(2)
    if row<source.shape[0] and col<source.shape[1]:out[col,row]=source[row,col]

def transpose(values):
    source=np.asarray(values,dtype=np.float32)
    out=np.zeros((source.shape[1],source.shape[0]),dtype=np.float32)
    blocks=((source.shape[0]+1)//2,(source.shape[1]+1)//2)
    transpose_kernel[blocks,(2,2)](source,out)
    return out
''',[('Transposes rectangular values','np.array_equal(transpose([[1,2,3],[4,5,6]]),[[1,4],[2,5],[3,6]])'),('Single element','np.array_equal(transpose([[9]]),[[9]])'),('Partial two-dimensional blocks','np.array_equal(transpose(np.arange(15).reshape(3,5)),np.arange(15).reshape(3,5).T)')],['2D launch','Guard both axes','Transpose'],cuda_ref)
add('cuda',5,'Cooperate with shared memory','Threads in a block can exchange values through shared memory. Synchronization creates a point all threads in that block must reach before continuing.','load shared values → barrier → reduce → write','Sum each block of eight input values into one output. Threads outside the input still write zero to shared memory and participate in every barrier. Returning early before a block-wide barrier is unsafe. The simulator does not qualify real hardware race behavior.',['Complete block_sum_kernel(values,out).','Load eight shared float32 values per block (zero-pad the final block), then synchronize.','Thread 0 sums all eight shared slots and writes one result for its block.'],'Every thread in a block must reach cuda.syncthreads; keep the barrier outside the bounds guard.',['Create shared=cuda.shared.array(8,dtype=float32).','Each thread fills shared[cuda.threadIdx.x], then call cuda.syncthreads().','Only thread 0 loops over the eight shared values and writes out[cuda.blockIdx.x].'],'''
import numpy as np
from numba import cuda, float32

@cuda.jit
def block_sum_kernel(values,out):
    pass

def block_sums(values):
    values=np.asarray(values,dtype=np.float32)
    blocks=(values.size+7)//8
    out=np.zeros(blocks,dtype=np.float32)
    if blocks:block_sum_kernel[blocks,8](values,out)
    return out
''','''
import numpy as np
from numba import cuda, float32

@cuda.jit
def block_sum_kernel(values,out):
    shared=cuda.shared.array(8,dtype=float32)
    tid=cuda.threadIdx.x
    i=cuda.grid(1)
    shared[tid]=values[i] if i<values.size else 0
    cuda.syncthreads()
    if tid==0:
        total=0.0
        for j in range(8):total+=shared[j]
        out[cuda.blockIdx.x]=total

def block_sums(values):
    values=np.asarray(values,dtype=np.float32)
    blocks=(values.size+7)//8
    out=np.zeros(blocks,dtype=np.float32)
    if blocks:block_sum_kernel[blocks,8](values,out)
    return out
''',[('Full block sum','np.allclose(block_sums(np.arange(8)),[28])'),('Partial last block','np.allclose(block_sums(np.arange(11)),[28,27])'),('Negative values','np.allclose(block_sums([-1,-2,-3]),[-6])'),('Empty input','block_sums([]).shape==(0,)')],['Shared memory','Block barrier','Block result'],cuda_ref)
add('cuda',6,'Fuse an ML operation','Combine a weighted sum and ReLU in one kernel: out=max(scale*a+b,0). This resembles a tiny piece of a neural-network computation.','out[i] = max(scale × a[i] + b[i], 0)','Fusing elementwise operations can reduce intermediate memory traffic on a GPU, but this simulator cannot demonstrate a speedup. First verify shapes and numerical values. A fair hardware benchmark must include warmup, synchronization, appropriate precision and a strong baseline.',['Implement fused_kernel(a,b,scale,out).','Compute the weighted sum, clamp negative results to zero, and guard the global index.','Use the provided explicit-transfer wrapper; pass all numerical checks before considering GPU benchmarking.'],'Correctness first; hardware performance claims require hardware measurements.',['Use i=cuda.grid(1), then check i<out.size.','Compute value=scale*a[i]+b[i].','Write value if value>0 else 0.'],'''
import numpy as np
from numba import cuda

@cuda.jit
def fused_kernel(a,b,scale,out):
    pass

def fused(a,b,scale):
    a=np.asarray(a,dtype=np.float32)
    b=np.asarray(b,dtype=np.float32)
    if a.size==0:return np.empty(0,dtype=np.float32)
    da,db=cuda.to_device(a),cuda.to_device(b)
    out=cuda.device_array(a.shape,dtype=np.float32)
    fused_kernel[(a.size+3)//4,4](da,db,scale,out)
    return out.copy_to_host()
''','''
import numpy as np
from numba import cuda

@cuda.jit
def fused_kernel(a,b,scale,out):
    i=cuda.grid(1)
    if i<out.size:
        value=scale*a[i]+b[i]
        out[i]=value if value>0 else 0

def fused(a,b,scale):
    a=np.asarray(a,dtype=np.float32)
    b=np.asarray(b,dtype=np.float32)
    if a.size==0:return np.empty(0,dtype=np.float32)
    da,db=cuda.to_device(a),cuda.to_device(b)
    out=cuda.device_array(a.shape,dtype=np.float32)
    fused_kernel[(a.size+3)//4,4](da,db,scale,out)
    return out.copy_to_host()
''',[('Weighted sum followed by ReLU','np.allclose(fused([-2,0,3],[1,-1,2],2),[0,0,8])'),('Different scale and partial block','np.allclose(fused([1,2,3,4,5],[5,4,3,2,1],-.5),[4.5,3,1.5,0,0])'),('Zero scale preserves positive bias','np.allclose(fused([7],[2],0),[2])'),('Empty batch','fused([],[],1).shape==(0,)')],['Copy inputs','Fused kernel','Validate output'],cuda_ref)
