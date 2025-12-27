# Temporal LangGraph Samples Proposal

This document proposes sample applications demonstrating the [Temporal LangGraph integration](https://github.com/temporalio/sdk-python/blob/main/temporalio/contrib/langgraph/README.md) - combining LangGraph's agent framework with Temporal's durable execution.

## Design Principles

Each sample should demonstrate:
1. **Durability** - Agents that survive failures and can resume from checkpoints
2. **Production Readiness** - Proper timeout/retry configuration, error handling
3. **Temporal Features** - Leveraging signals, queries, child workflows where appropriate

Samples are organized by complexity and use case, inspired by [OpenAI Agents samples](../openai_agents/README.md) structure.

---

## Proposed Samples

### 1. Basic Examples (`basic/`)

#### 1.1 Hello World Agent
**Description:** Minimal LangGraph agent with Temporal integration. Single-node graph that processes a query.

**Demonstrates:**
- Basic plugin setup and graph registration
- Simple workflow invocation
- Activity-based node execution

**Original Reference:** N/A (custom introductory example)

---

#### 1.2 ReAct Agent with Tools
**Description:** Classic ReAct (Reasoning + Acting) agent that can use tools to answer questions. Implements the think-act-observe loop.

**Demonstrates:**
- LangChain's `create_agent` with Temporal integration
- Durable execution where each node runs as a Temporal activity
- Automatic retries and crash recovery at the node level
- Cyclic graph execution (agent → tools → agent → ...)

**Original Reference:** [LangGraph ReAct Agent Template](https://github.com/langchain-ai/react-agent)

---

### 2. Human-in-the-Loop (`human_in_loop/`)

#### 2.1 Approval Workflow
**Description:** Agent that pauses for human approval before taking actions. Uses LangGraph's `interrupt()` with Temporal signals.

**Demonstrates:**
- `interrupt()` for pausing execution
- Temporal signals for receiving human input
- Workflow queries for checking pending approvals
- Timeout handling for approval deadlines

**Original Reference:** [LangGraph Human-in-the-Loop Guide](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/)

---

#### 2.2 Document Review Agent
**Description:** Agent that drafts documents and requests human review/edits before finalizing. Supports iterative refinement cycles.

**Demonstrates:**
- Multi-step interrupt/resume cycles
- State preservation across interrupts
- Combining AI drafting with human editing

**Original Reference:** [LangGraph Human Feedback Discussion](https://github.com/langchain-ai/langgraph/discussions/1137)

---

### 3. Multi-Agent Systems (`multi_agent/`)

#### 3.1 Supervisor Agent
**Description:** Supervisor that coordinates specialized worker agents (researcher, writer, critic). The supervisor routes tasks to appropriate agents and aggregates results.

**Demonstrates:**
- Multi-agent orchestration patterns
- Supervisor decision-making logic
- Agent handoffs and communication
- Parallel agent execution with `Send`

**Original Reference:** [LangGraph Supervisor Library](https://github.com/langchain-ai/langgraph-supervisor-py) | [Multi-Agent Blog Post](https://blog.langchain.com/langgraph-multi-agent-workflows/)

---

#### 3.2 Hierarchical Agent Teams
**Description:** Two-level hierarchy with a top supervisor managing team supervisors (research team + writing team), each with their own worker agents.

**Demonstrates:**
- Child workflows for team isolation
- Hierarchical agent coordination
- Complex routing logic
- Cross-team communication

**Original Reference:** [LangGraph Hierarchical Agent Teams Tutorial](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams/)

---

### 4. RAG and Research (`rag/`)

#### 4.1 Agentic RAG
**Description:** RAG agent that decides when to retrieve documents vs. respond directly. Includes document relevance grading and query rewriting.

**Demonstrates:**
- Conditional retrieval decisions
- Document grading nodes
- Query rewriting for better retrieval
- Combining retrieval with generation

**Original Reference:** [LangGraph Agentic RAG Tutorial](https://github.com/langchain-ai/langgraph/blob/main/examples/rag/langgraph_agentic_rag.ipynb) | [Agentic RAG Docs](https://docs.langchain.com/oss/python/langgraph/agentic-rag)

---

#### 4.2 Corrective RAG
**Description:** Self-correcting RAG that validates retrieved documents and falls back to web search when needed. Includes hallucination detection.

**Demonstrates:**
- Document relevance validation
- Fallback to web search
- Self-correction loops
- Multiple retrieval strategies

**Original Reference:** [Corrective RAG Guide](https://www.analyticsvidhya.com/blog/2024/07/building-agentic-rag-systems-with-langgraph/)

---

#### 4.3 Deep Research Agent
**Description:** Multi-step research agent that performs iterative web searches, evaluates results, and synthesizes findings into a comprehensive report.

**Demonstrates:**
- Long-running research workflows (minutes to hours)
- Parallel search execution
- Result evaluation and iteration
- Continue-as-new for large histories
- Report generation

**Original Reference:** [LangGraph Deep Research Agent](https://towardsdatascience.com/langgraph-101-lets-build-a-deep-research-agent/) | [Exa Research System](https://blog.langchain.com/exa/)

---

### 5. Customer Service (`customer_service/`)

#### 5.1 Customer Support Agent
**Description:** Interactive customer service agent that handles inquiries, accesses knowledge bases, and escalates to humans when needed.

**Demonstrates:**
- Conversational state management
- Knowledge base integration
- Escalation workflows with `interrupt()`
- Session continuity across interactions

**Original Reference:** [LangGraph Customer Support Tutorial](https://github.com/langchain-ai/langgraph/blob/main/docs/docs/tutorials/customer-support/customer-support.ipynb)

---

#### 5.2 Email Triage Agent
**Description:** Agent that processes incoming emails, categorizes them, drafts responses using RAG for policy questions, and routes to appropriate handlers.

**Demonstrates:**
- Email classification
- RAG for policy/knowledge lookup
- Conditional routing based on email type
- Draft review before sending

**Original Reference:** [Agentic RAG Customer Support](https://blog.lancedb.com/agentic-rag-using-langgraph-building-a-simple-customer-support-autonomous-agent/)

---

### 6. Planning and Execution (`planning/`)

#### 6.1 Plan-and-Execute Agent
**Description:** Agent that first creates a plan, then executes steps sequentially, with the ability to replan based on results.

**Demonstrates:**
- Separation of planning and execution
- Dynamic replanning
- Step-by-step execution with checkpointing
- Plan validation

**Original Reference:** [LangGraph Plan-and-Execute Tutorial](https://github.com/langchain-ai/langgraph/blob/main/examples/plan-and-execute/plan-and-execute.ipynb)

---

#### 6.2 Travel Planning Agent
**Description:** Agent that plans trips by coordinating flight searches, hotel bookings, and itinerary creation with user preferences.

**Demonstrates:**
- Multi-tool coordination
- User preference handling
- Complex planning with constraints
- Real API integration patterns

**Original Reference:** [LangGraph Travel Planning Tutorial](https://www.projectpro.io/article/langgraph/1109)

---

### 7. Code and Development (`code/`)

#### 7.1 Code Assistant
**Description:** Agent that helps with code-related tasks: explaining code, generating code, debugging, and answering programming questions.

**Demonstrates:**
- Code-aware prompting
- Multi-turn coding conversations
- Tool use for code execution/testing
- Context management for large codebases

**Original Reference:** [LangGraph Code Assistant Tutorial](https://github.com/langchain-ai/langgraph/blob/main/examples/code_assistant/langgraph_code_assistant.ipynb)

---

### 8. Advanced Patterns (`advanced/`)

#### 8.1 Reflection Agent
**Description:** Agent that generates output, reflects on it, and iteratively improves until quality criteria are met.

**Demonstrates:**
- Self-critique and improvement loops
- Quality evaluation nodes
- Iterative refinement patterns
- Loop termination conditions

**Original Reference:** [LangGraph Reflection Tutorial](https://github.com/langchain-ai/langgraph/tree/main/docs/docs/tutorials/reflection)

---

#### 8.2 Tree of Thoughts
**Description:** Agent that explores multiple reasoning paths in parallel and selects the best solution.

**Demonstrates:**
- Parallel exploration with `Send`
- Solution evaluation and ranking
- Branch pruning logic
- Complex graph patterns

**Original Reference:** [LangGraph Tree of Thoughts Tutorial](https://github.com/langchain-ai/langgraph/tree/main/docs/docs/tutorials/tot)

---

#### 8.3 Long-Running Workflow with Checkpointing
**Description:** Demonstrates continue-as-new for workflows that may run for extended periods and generate large event histories.

**Demonstrates:**
- `should_continue` callback for checkpointing
- State serialization and restoration
- Continue-as-new pattern
- Store API for cross-workflow data

**Original Reference:** N/A (Temporal-specific pattern)

---

## Implementation Priority

### Phase 1 - Core Examples (Recommended First)
1. **Basic: Hello World Agent** - Entry point for new users
2. **Basic: ReAct Agent with Tools** - Most common agent pattern
3. **Human-in-the-Loop: Approval Workflow** - Key differentiator for Temporal
4. **RAG: Agentic RAG** - Popular production use case

### Phase 2 - Multi-Agent and Research
5. **Multi-Agent: Supervisor Agent** - Popular advanced pattern
6. **RAG: Deep Research Agent** - Showcases long-running durability
7. **Customer Service: Support Agent** - Business-relevant example

### Phase 3 - Advanced Patterns
8. **Planning: Plan-and-Execute** - Structured agent execution
9. **Advanced: Reflection Agent** - Self-improvement pattern
10. **Multi-Agent: Hierarchical Teams** - Complex orchestration

---

## Directory Structure

```
langgraph/
├── README.md                    # Overview and getting started
├── __init__.py
├── basic/
│   ├── README.md
│   ├── hello_world/
│   │   ├── README.md
│   │   ├── run_worker.py
│   │   └── run_workflow.py
│   └── react_agent/
│       ├── README.md
│       ├── agent.py
│       ├── tools.py
│       ├── run_worker.py
│       └── run_workflow.py
├── human_in_loop/
│   ├── README.md
│   ├── approval_workflow/
│   └── document_review/
├── multi_agent/
│   ├── README.md
│   ├── supervisor/
│   └── hierarchical_teams/
├── rag/
│   ├── README.md
│   ├── agentic_rag/
│   ├── corrective_rag/
│   └── deep_research/
├── customer_service/
│   ├── README.md
│   ├── support_agent/
│   └── email_triage/
├── planning/
│   ├── README.md
│   ├── plan_and_execute/
│   └── travel_planner/
├── code/
│   ├── README.md
│   └── code_assistant/
└── advanced/
    ├── README.md
    ├── reflection/
    ├── tree_of_thoughts/
    └── long_running_workflow/
```

---

## References

### Official LangGraph Resources
- [LangGraph Documentation](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph GitHub Repository](https://github.com/langchain-ai/langgraph)
- [LangGraph Tutorials](https://github.com/langchain-ai/langgraph/tree/main/docs/docs/tutorials)
- [LangChain Academy - Intro to LangGraph](https://academy.langchain.com/courses/intro-to-langgraph)

### Multi-Agent Resources
- [LangGraph Multi-Agent Concepts](https://github.com/langchain-ai/langgraph/blob/main/docs/docs/concepts/multi_agent.md)
- [LangGraph Supervisor Library](https://github.com/langchain-ai/langgraph-supervisor-py)
- [Hierarchical Agent Teams Tutorial](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams/)

### RAG and Research
- [Agentic RAG Documentation](https://docs.langchain.com/oss/python/langgraph/agentic-rag)
- [RAG Research Agent Template](https://github.com/langchain-ai/rag-research-agent-template)
- [Deep Research Agent Article](https://towardsdatascience.com/langgraph-101-lets-build-a-deep-research-agent/)

### Human-in-the-Loop
- [Human-in-the-Loop How-To](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/)
- [Human Feedback Discussion](https://github.com/langchain-ai/langgraph/discussions/1137)

### Courses and Tutorials
- [DeepLearning.AI - AI Agents in LangGraph](https://www.deeplearning.ai/short-courses/ai-agents-in-langgraph/)
- [Real Python - LangGraph Tutorial](https://realpython.com/langgraph-python/)
