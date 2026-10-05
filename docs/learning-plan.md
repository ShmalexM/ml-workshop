# A simple way to use ML Workshop

Use one lesson per sitting. Ten to twenty focused minutes is a useful starting point; the in-app times are estimates rather than deadlines.

1. Read the short explanation and diagram. Predict what the starter code will output.
2. Run it, then replace the TODO. Use print statements to inspect shapes and values.
3. Check your answer. Treat failed assertions as clues about the behavior you need.
4. Write two sentences in Notes: what the concept does and a mistake to avoid.
5. On your next visit, redo the previous lesson without its solution before continuing.

Progression:

```mermaid
flowchart LR
 A[ML foundations] --> B[PyTorch]
 B --> C[TensorFlow]
 C --> D[Modern AI stack]
 B --> E[CUDA Python]
 E --> F[NVIDIA hardware practice later]
```

Start with the six foundation lessons. They make loss functions, gradients, data splitting and training loops concrete in Python. PyTorch and TensorFlow then solve the same kinds of problems so you can distinguish concepts from API names. The modern AI exercises use local framework primitives; they do not pretend that a randomly initialized model is trained or that a prompt template is an LLM. CUDA kernels run in CPU simulation in ML Workshop, and actual device compilation and performance remain separate practice.

At each capstone, change the data or inputs and explain the resulting behavior. A passed exercise alone is not job readiness; use these exercises to build the foundation for a larger project, documented evaluation and real deployment experience.
