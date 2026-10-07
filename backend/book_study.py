"""Reading guides with source locations and related lessons."""
# These printed-page locators were checked against this PDF edition. Other
# editions/formats remain readable, but must not be linked to unrelated pages.
INFERENCE_GUIDE_EDITION = 'b297183c38ffc7ffa30100e1aab0af3b1c20b49778939ee976522fe39ac0df89'
GUIDES = [{'id': 'gpu-threads',
  'bookId': 'gpu-glossary',
  'title': 'From a kernel to a grid',
  'readings': [('device-software--kernel', 'CUDA kernel'),
               ('device-software--thread-block', 'Thread blocks'),
               ('device-software--thread-block-grid', 'Grids')],
  'focus': 'Follow the code that one thread runs, then count the work done by the whole '
           'launch.',
  'question': 'For 130 elements and 64 threads per block, how many blocks do you launch, and '
              'which threads must skip their writes?',
  'lessons': ['cuda-1', 'cuda-2']},
 {'id': 'gpu-hardware',
  'bookId': 'gpu-glossary',
  'title': 'Map software to hardware',
  'readings': [('device-hardware--streaming-multiprocessor', 'Streaming multiprocessors'),
               ('device-hardware--streaming-multiprocessor-architecture', 'SM architecture'),
               ('device-hardware--tensor-core', 'Tensor cores')],
  'focus': 'Compare the thread and block names in code with the GPU hardware that runs them.',
  'question': 'Explain the difference between a CUDA thread, a warp, a streaming '
              'multiprocessor, and a tensor core without treating them as interchangeable.',
  'lessons': ['cuda-1']},
 {'id': 'gpu-memory',
  'bookId': 'gpu-glossary',
  'title': 'Choose where data lives',
  'readings': [('device-software--memory-hierarchy', 'Memory hierarchy'),
               ('device-software--shared-memory', 'Shared memory'),
               ('device-software--global-memory', 'Global memory')],
  'focus': 'Choose which values belong to one thread, one block, or the whole device.',
  'question': 'In the shared-memory exercise, which values must be visible to another thread, '
              'and why is a block barrier needed before reading them?',
  'lessons': ['cuda-3', 'cuda-5', 'cuda-6']},
 {'id': 'gpu-warps',
  'bookId': 'gpu-glossary',
  'title': 'Reason about warp behavior',
  'readings': [('device-software--warp', 'Warps'),
               ('perf--warp-divergence', 'Warp divergence'),
               ('perf--occupancy', 'Occupancy')],
  'focus': 'Use GPU profiling to inspect thread behavior that the CPU simulator cannot '
           'measure.',
  'question': 'Why can a kernel produce the right result in simulation while still needing '
              'hardware profiling for divergence and occupancy?',
  'lessons': ['cuda-2', 'cuda-4']},
 {'id': 'gpu-roofline',
  'bookId': 'gpu-glossary',
  'title': 'Identify the limiting resource',
  'readings': [('perf--arithmetic-intensity', 'Arithmetic intensity'),
               ('perf--roofline-model', 'The roofline model'),
               ('perf--memory-bound', 'Memory-bound work')],
  'focus': 'Compare arithmetic work with bytes moved to find what could limit speed.',
  'question': 'If an algorithm reuses loaded values twice as much while doing the same useful '
              'arithmetic, which direction does its point move on a roofline plot? What still '
              'needs measurement?',
  'lessons': ['cuda-6', 'pytorch-6', 'tensorflow-6']},
 {'id': 'gpu-access',
  'bookId': 'gpu-glossary',
  'title': 'Follow the memory accesses',
  'readings': [('perf--memory-coalescing', 'Memory coalescing'),
               ('perf--bank-conflict', 'Bank conflicts'),
               ('perf--register-pressure', 'Register pressure')],
  'focus': 'Read the diagrams at full size, then draw the addresses each thread accesses.',
  'question': 'Sketch the addresses read by adjacent threads. Which accesses are contiguous, '
              'and which compete for the same shared-memory bank?',
  'lessons': ['cuda-4', 'cuda-5', 'cuda-6']},
 {'id': 'gpu-tools',
  'bookId': 'gpu-glossary',
  'title': 'Know the toolchain',
  'readings': [('host-software--nvcc', 'nvcc'),
               ('host-software--nsight-systems', 'Nsight Systems'),
               ('host-software--cuda-graph', 'CUDA graphs')],
  'focus': 'Identify the tools used to compile, run, and profile GPU code.',
  'question': 'Which tool compiles a kernel, which inspects workload timing, and which reduces '
              'repeated launch overhead? What would you measure on the GPU?',
  'lessons': ['cuda-6']},
 {'id': 'inference-metrics',
  'bookId': 'inference-engineering',
  'title': 'Define what fast means',
  'readings': [(37, 'Latency and throughput · pp. 35–37'), (38, 'Latency percentiles · p. 36')],
  'focus': 'Set targets for response time and the number of requests a service can handle.',
  'question': 'For a streaming application, write separate targets for time to first token, '
              'token generation rate, and p95 latency. Which would an average hide?',
  'lessons': ['reliability-4']},
 {'id': 'inference-phases',
  'bookId': 'inference-engineering',
  'title': 'Trace prefill and decode',
  'readings': [(48, 'LLM inference mechanics · p. 46'),
               (54, 'Attention · p. 52'),
               (65, 'LLM bottlenecks · p. 63')],
  'focus': 'Follow a prompt’s initial processing and the repeated work used to generate later '
           'tokens.',
  'question': 'Draw the work performed before the first output token and the work repeated for '
              'each later token. Where can previously computed state be reused?',
  'lessons': ['modern-1', 'modern-2']},
 {'id': 'inference-bottleneck',
  'bookId': 'inference-engineering',
  'title': 'Estimate compute and memory needs',
  'readings': [(63, 'Calculating bottlenecks · p. 61'),
               (64, 'Arithmetic intensity · p. 62'),
               (76, 'GPU architecture · p. 74'),
               (78, 'Memory and caches · p. 76')],
  'focus': 'Estimate the compute and memory needed for one inference request.',
  'question': 'Write down the compute, model-weight memory, and memory-traffic assumptions for '
              'an inference request. Which estimates are lower bounds rather than predictions?',
  'lessons': ['cuda-3', 'cuda-6', 'pytorch-1', 'tensorflow-1']},
 {'id': 'inference-software',
  'bookId': 'inference-engineering',
  'title': 'Follow frameworks through to kernels',
  'readings': [(98, 'CUDA · p. 96'),
               (102, 'Kernel fusion · p. 100'),
               (104, 'PyTorch · p. 102'),
               (107, 'Inference engines · p. 105')],
  'focus': 'Follow a request from application code to the kernels that do the calculations.',
  'question': 'Draw a request flowing from an application through an inference engine and '
              'framework into GPU kernels. Where could kernel fusion reduce traffic?',
  'lessons': ['pytorch-6', 'tensorflow-6', 'modern-4', 'cuda-6']},
 {'id': 'inference-quantization',
  'bookId': 'inference-engineering',
  'title': 'Trade memory for numerical precision',
  'readings': [(122, 'Quantization · p. 120'),
               (123, 'Number formats · p. 121'),
               (130, 'Measuring quality impact · p. 128')],
  'focus': 'Estimate how a lower bit width changes weight storage, then plan how to check '
           'prediction quality.',
  'question': 'Estimate raw storage for 7 billion weights at 16 bits and at 4 bits. What '
              'metadata, runtime state, and quality measurements are missing from that '
              'estimate?',
  'lessons': ['pytorch-1', 'tensorflow-1']},
 {'id': 'inference-cache',
  'bookId': 'inference-engineering',
  'title': 'Understand the KV cache',
  'readings': [(138, 'Prefix and KV caching · p. 136'),
               (141, 'Where to store the cache · p. 139'),
               (143, 'Long context · p. 141')],
  'focus': 'Identify the attention state that can be reused and the memory it occupies.',
  'question': 'What input prefix must match for cached state to be reusable? Explain why a '
              'retrieval-result cache and an attention KV cache store different things.',
  'lessons': ['modern-2', 'modern-5', 'modern-6']},
 {'id': 'inference-parallelism',
  'bookId': 'inference-engineering',
  'title': 'Scale across devices',
  'readings': [(144, 'Model parallelism · p. 142'),
               (146, 'Tensor parallelism · p. 144'),
               (150, 'Disaggregation · p. 148')],
  'focus': 'Compare splitting a model across devices with running different inference phases '
           'on different devices.',
  'question': 'What must move between devices in each design, and when could communication '
              'erase the expected compute benefit?',
  'lessons': ['cuda-3', 'cuda-6', 'modern-2']},
 {'id': 'inference-production',
  'bookId': 'inference-engineering',
  'title': 'Build a serving experiment',
  'readings': [(114, 'Benchmarking · p. 112'),
               (185, 'Autoscaling · p. 183'),
               (188, 'Concurrency and batching · p. 186'),
               (205, 'Observability · p. 203')],
  'focus': 'Write a repeatable load test with a workload and clear pass conditions.',
  'question': 'Specify a workload, concurrency sweep, warmup, latency percentiles, throughput, '
              'error rate, and quality check. Which signals would tell you to stop increasing '
              'concurrency?',
  'lessons': ['reliability-4', 'data-4']}]

def study_guides(library, lesson_id=None):
    result = []
    for guide in GUIDES:
        if lesson_id and lesson_id not in guide['lessons']:
            continue
        try:
            book = library.book(guide['bookId'])
        except KeyError:
            continue
        if guide['bookId'] == 'inference-engineering' and (book['format'] != 'pdf' or book['sha256'] != INFERENCE_GUIDE_EDITION):
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
