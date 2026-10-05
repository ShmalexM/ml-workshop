"""Original study prompts and source locators, not redistributed book excerpts."""
GUIDES = [
    dict(id='gpu-threads',bookId='gpu-glossary',title='From a kernel to a grid',
         readings=[('device-software--kernel','CUDA kernel'),('device-software--thread-block','Thread blocks'),('device-software--thread-block-grid','Grids')],
         focus='Connect the code written by one thread to the work created by a whole launch.',
         question='For 130 elements and 64 threads per block, how many blocks do you launch, and which threads must skip their writes?',
         lessons=['cuda-1','cuda-2']),
    dict(id='gpu-hardware',bookId='gpu-glossary',title='Map software to hardware',
         readings=[('device-hardware--streaming-multiprocessor','Streaming multiprocessors'),('device-hardware--streaming-multiprocessor-architecture','SM architecture'),('device-hardware--tensor-core','Tensor cores')],
         focus='Distinguish programming abstractions from the hardware that schedules and executes them.',
         question='Explain the difference between a CUDA thread, a warp, a streaming multiprocessor, and a tensor core without treating them as interchangeable.',
         lessons=['cuda-1','pytorch-1','tensorflow-1']),
    dict(id='gpu-memory',bookId='gpu-glossary',title='Choose where data lives',
         readings=[('device-software--memory-hierarchy','Memory hierarchy'),('device-software--shared-memory','Shared memory'),('device-software--global-memory','Global memory')],
         focus='Separate thread-private, block-shared, and device-wide data.',
         question='In the shared-memory exercise, which values must be visible to another thread, and why is a block barrier needed before reading them?',
         lessons=['cuda-3','cuda-5','cuda-6']),
    dict(id='gpu-warps',bookId='gpu-glossary',title='Reason about warp behavior',
         readings=[('device-software--warp','Warps'),('perf--warp-divergence','Warp divergence'),('perf--occupancy','Occupancy')],
         focus='Learn what CPU simulation cannot tell you about real GPU execution.',
         question='Why can a kernel produce the right result in simulation while still needing hardware profiling for divergence and occupancy?',
         lessons=['cuda-2','cuda-4']),
    dict(id='gpu-roofline',bookId='gpu-glossary',title='Identify the limiting resource',
         readings=[('perf--arithmetic-intensity','Arithmetic intensity'),('perf--roofline-model','The roofline model'),('perf--memory-bound','Memory-bound work')],
         focus='Relate operations, bytes moved, and hardware throughput limits.',
         question='If an algorithm reuses loaded values twice as much while doing the same useful arithmetic, which direction does its point move on a roofline plot? What still needs measurement?',
         lessons=['cuda-6','pytorch-6','tensorflow-6']),
    dict(id='gpu-access',bookId='gpu-glossary',title='Follow the memory accesses',
         readings=[('perf--memory-coalescing','Memory coalescing'),('perf--bank-conflict','Bank conflicts'),('perf--register-pressure','Register pressure')],
         focus='Study the original diagrams at full size before drawing your own access pattern.',
         question='Sketch the addresses read by adjacent threads. Which accesses are contiguous, and which compete for the same shared-memory bank?',
         lessons=['cuda-4','cuda-5','cuda-6']),
    dict(id='gpu-tools',bookId='gpu-glossary',title='Know the toolchain',
         readings=[('host-software--nvcc','nvcc'),('host-software--nsight-systems','Nsight Systems'),('host-software--cuda-graph','CUDA graphs')],
         focus='Place compilation, execution, and profiling in different parts of the workflow.',
         question='Which tool would you use to compile a kernel, inspect time across a workload, and reduce repeated launch overhead? Do not substitute simulator timing for a device measurement.',
         lessons=['cuda-6']),
    dict(id='inference-metrics',bookId='inference-engineering',title='Define what fast means',
         readings=[(37,'Latency and throughput · pp. 35–37'),(38,'Latency percentiles · p. 36')],
         focus='Choose metrics that describe a user’s experience and the service’s capacity separately.',
         question='For a streaming application, write separate targets for time to first token, token generation rate, and p95 latency. Which would an average hide?',
         lessons=['pytorch-6','tensorflow-6','modern-2']),
    dict(id='inference-phases',bookId='inference-engineering',title='Trace prefill and decode',
         readings=[(48,'LLM inference mechanics · p. 46'),(54,'Attention · p. 52'),(65,'LLM bottlenecks · p. 63')],
         focus='Follow one prompt through its initial processing and subsequent token generation.',
         question='Draw the work performed before the first output token and the work repeated for each later token. Where can previously computed state be reused?',
         lessons=['modern-1','modern-2']),
    dict(id='inference-bottleneck',bookId='inference-engineering',title='Connect model work to hardware',
         readings=[(63,'Calculating bottlenecks · p. 61'),(64,'Arithmetic intensity · p. 62'),(76,'GPU architecture · p. 74'),(78,'Memory and caches · p. 76')],
         focus='Estimate limiting resources before choosing an optimization.',
         question='Write down the compute, model-weight memory, and memory-traffic assumptions for an inference request. Which estimates are lower bounds rather than predictions?',
         lessons=['cuda-3','cuda-6','pytorch-1','tensorflow-1']),
    dict(id='inference-software',bookId='inference-engineering',title='Connect frameworks, kernels, and engines',
         readings=[(98,'CUDA · p. 96'),(102,'Kernel fusion · p. 100'),(104,'PyTorch · p. 102'),(107,'Inference engines · p. 105')],
         focus='Place your framework code within the full serving stack.',
         question='Draw a request flowing from an application through an inference engine and framework into GPU kernels. Where could kernel fusion reduce traffic?',
         lessons=['pytorch-6','tensorflow-6','modern-4','cuda-6']),
    dict(id='inference-quantization',bookId='inference-engineering',title='Trade memory for numerical precision',
         readings=[(122,'Quantization · p. 120'),(123,'Number formats · p. 121'),(130,'Measuring quality impact · p. 128')],
         focus='Treat a smaller representation as a change that requires both quality and performance evaluation.',
         question='Estimate raw storage for 7 billion weights at 16 bits and at 4 bits. What metadata, runtime state, and quality measurements are missing from that estimate?',
         lessons=['foundations-2','foundations-4','pytorch-1','tensorflow-1']),
    dict(id='inference-cache',bookId='inference-engineering',title='Understand the KV cache',
         readings=[(138,'Prefix and KV caching · p. 136'),(141,'Where to store the cache · p. 139'),(143,'Long context · p. 141')],
         focus='Reason about reusable attention state and the memory cost of long contexts.',
         question='What input prefix must match for cached state to be reusable? Explain why a retrieval-result cache and an attention KV cache store different things.',
         lessons=['modern-2','modern-5','modern-6']),
    dict(id='inference-parallelism',bookId='inference-engineering',title='Scale across devices',
         readings=[(144,'Model parallelism · p. 142'),(146,'Tensor parallelism · p. 144'),(150,'Disaggregation · p. 148')],
         focus='Compare splitting model work with separating inference phases.',
         question='What must move between devices in each design, and when could communication erase the expected compute benefit?',
         lessons=['cuda-3','cuda-6','modern-2']),
    dict(id='inference-production',bookId='inference-engineering',title='Build a serving experiment',
         readings=[(114,'Benchmarking · p. 112'),(185,'Autoscaling · p. 183'),(188,'Concurrency and batching · p. 186'),(205,'Observability · p. 203')],
         focus='Turn optimization claims into a repeatable load test with clear acceptance criteria.',
         question='Specify a workload, concurrency sweep, warmup, latency percentiles, throughput, error rate, and quality check. Which signals would tell you to stop increasing concurrency?',
         lessons=['foundations-4','pytorch-6','tensorflow-6','modern-6']),
]

def study_guides(library, lesson_id=None):
    result = []
    for guide in GUIDES:
        if lesson_id and lesson_id not in guide['lessons']:
            continue
        try:
            book = library.book(guide['bookId'])
        except KeyError:
            continue
        keys = {item.get('key'):item['location'] for item in book['toc']}
        readings = []
        for locator,title in guide['readings']:
            location = locator if isinstance(locator,int) else keys.get(locator)
            if location and 1<=location<=book['count']:
                readings.append(dict(location=location,title=title))
        if readings:
            result.append({**guide,'readings':readings,'bookTitle':book['title']})
    return result
