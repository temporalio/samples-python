# Reflection Agent

An agent that generates content, critiques it, and iteratively improves until quality criteria are met. This demonstrates the self-reflection pattern for producing higher-quality outputs.

## Overview

The Reflection Agent implements a generate-critique-revise loop:
1. **Generate** - Create initial content based on the task
2. **Reflect** - Critique the content with structured feedback
3. **Revise** - Improve content based on the critique
4. **Evaluate** - Check if quality criteria are met
5. **Loop** - Repeat until satisfied or max iterations reached

## Why Reflection?

The reflection pattern improves output quality by:
- **Self-correction**: Catching and fixing issues automatically
- **Structured feedback**: Using specific criteria for evaluation
- **Iterative refinement**: Multiple passes produce better results
- **Visibility**: Each iteration's critique is recorded

## Why Temporal?

Temporal enhances reflection workflows with:
- **Durability**: Long refinement sessions complete reliably
- **Visibility**: See each iteration in the workflow history
- **Checkpointing**: Resume from any iteration if interrupted
- **Cost tracking**: Monitor LLM calls across iterations

## Architecture

```
[Generate] --> [Reflect] --> [Score >= 7?] --> YES --> [Finalize] --> END
                   ^              |
                   |              NO
                   |              v
                   +-------- [Revise]
```

Each node runs as a Temporal activity with automatic retry.

## Running the Sample

### Prerequisites

- Temporal server running locally
- OpenAI API key

### Steps

1. Start the Temporal server:
   ```bash
   temporal server start-dev
   ```

2. In one terminal, start the worker:
   ```bash
   export OPENAI_API_KEY=your-key-here
   uv run langgraph_plugin/graph_api/reflection/run_worker.py
   ```

3. In another terminal, run the workflow:
   ```bash
   uv run langgraph_plugin/graph_api/reflection/run_workflow.py
   ```

## Sample Output

```
============================================================
REFLECTION JOURNEY
============================================================

Iteration 1 Critique:
  Score: 5/10
  Strengths: Clear structure, Good opening hook
  Weaknesses: Too generic, Lacks specific examples

Iteration 2 Critique:
  Score: 7/10
  Strengths: Specific examples added, Better flow
  Weaknesses: Could be more concise

============================================================
FINAL CONTENT
============================================================

In the world of AI agents, failure is not just possible—it's inevitable.
Network requests timeout, APIs rate-limit, and worker processes crash.
Without durable execution, these failures mean lost progress, corrupted
state, and frustrated users...

[Rest of the refined blog post]
```

## Key Features Demonstrated

### 1. Structured Critique
```python
class Critique(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    quality_score: int  # 1-10
    is_satisfactory: bool  # True if score >= 7
```

### 2. Quality-Based Routing
```python
def should_revise(state) -> Literal["revise", "finalize"]:
    if critique.is_satisfactory or iteration >= max_iterations:
        return "finalize"
    return "revise"
```

### 3. Feedback-Driven Revision
```python
def revise(state: ReflectionState) -> dict[str, Any]:
    feedback = format_critique(latest_critique)
    revised = revision_chain.invoke({
        "task": task,
        "draft": draft,
        "feedback": feedback
    })
    return {"current_draft": revised, "iteration": iteration + 1}
```

## Customization

### Adjusting Quality Threshold

Change when content is considered "good enough":

```python
class Critique(BaseModel):
    is_satisfactory: bool = Field(
        description="Whether content meets standards (score >= 8)"  # Stricter
    )
```

### Adding Domain-Specific Criteria

Customize the critique for specific content types:

```python
reflect_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a technical writing editor. Evaluate:
    - Technical accuracy
    - Code example correctness
    - Appropriate complexity level
    - SEO optimization
    ..."""),
    ...
])
```

### Different Models for Generation vs Critique

Use different models for each role:

```python
# Creative model for generation
generator = ChatOpenAI(model="gpt-4", temperature=0.8)

# Precise model for critique
critic = ChatOpenAI(model="gpt-4", temperature=0)
```

## Use Cases

The reflection pattern works well for:
- **Writing tasks**: Blog posts, documentation, emails
- **Code generation**: Self-reviewing generated code
- **Problem-solving**: Iteratively refining solutions
- **Summarization**: Improving summary quality
- **Translation**: Self-correcting translations

## Comparison with Single-Pass Generation

| Aspect | Single-Pass | Reflection |
|--------|-------------|------------|
| Quality | Variable | Consistently higher |
| Cost | 1 LLM call | 3-6+ LLM calls |
| Latency | Fast | Slower |
| Transparency | Low | High (visible iterations) |
| Best for | Quick drafts | Final outputs |

## Next Steps

- Add human-in-the-loop for critique approval
- Implement specialized critics (grammar, style, accuracy)
- Add A/B testing of different revision strategies
- Integrate with external quality metrics
