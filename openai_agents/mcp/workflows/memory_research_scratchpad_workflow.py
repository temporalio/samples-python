from __future__ import annotations

from agents import Agent, Runner, trace
from agents.model_settings import ModelSettings
from temporalio import workflow
from temporalio.contrib import openai_agents as temporal_openai_agents

SEED_NOTES = [
    (
        "scratchpad/ai-sum/001",
        "Study A (2024-04)",
        "Summaries reduced triage time by 22% (n=60).",
        ["ai-summarization", "email", "kpi"],
    ),
    (
        "scratchpad/ai-sum/002",
        "User preference",
        "Users prefer action-first summaries with 5–8 bullets max.",
        ["ai-summarization", "email", "ux"],
    ),
    (
        "scratchpad/ai-sum/003",
        "Risk: misleading summaries",
        "Hallucination risk; mitigation: confidence thresholds + easy fallback to original email.",
        ["ai-summarization", "email", "risk"],
    ),
    (
        "scratchpad/ai-sum/004",
        "Latency consideration",
        "Cold-start latency noticeable on first open; can cache or precompute in background.",
        ["ai-summarization", "email", "perf"],
    ),
    (
        "scratchpad/ai-sum/005",
        "Adoption insight",
        "Admin controls improve enterprise adoption; opt-in increases trust and perceived control.",
        ["ai-summarization", "email", "adoption"],
    ),
]


@workflow.defn
class MemoryResearchScratchpadWorkflow:
    @workflow.run
    async def run(self) -> str:
        async with temporal_openai_agents.workflow.stateful_mcp_server(
            "MemoryServer",
        ) as server:
            with trace(workflow_name="MCP Memory Scratchpad Example"):
                agent = Agent(
                    name="Research Scratchpad Agent",
                    instructions=(
                        "Use the Memory MCP tools to persist, query, update, and delete notes."
                        " Keep IDs short and consistent. Synthesis must rely only on recalled notes and include simple"
                        " citations of the form '(Note: id)'. Keep the brief to 5 bullets."
                    ),
                    mcp_servers=[server],
                    model_settings=ModelSettings(tool_choice="required"),
                )

                # Step 1: Write seed notes to memory
                write_prompt_lines = [
                    "Store the following notes in memory. Use the given id and tags for each entry.",
                    "After storing, confirm each (id, tags) that was written.",
                    "",
                ]
                for note_id, title, content, tags in SEED_NOTES:
                    # Store tags as separate observation lines so search can reliably match them
                    tag_obs = ", ".join([f"tag: {t}" for t in tags])
                    write_prompt_lines.append(
                        f"- id: {note_id}; title: {title}; content: {content}; observations: [{tag_obs}]"
                    )
                write_prompt = "\n".join(write_prompt_lines)
                workflow.logger.info("Writing seed notes to memory")
                r1 = await Runner.run(starting_agent=agent, input=write_prompt)

                # Step 2: Query by tags
                query_prompt = (
                    "Search memory for notes that contain BOTH observations 'tag: ai-summarization' and 'tag: email'. "
                    "If the search returns empty, list entities with the name prefix 'scratchpad/ai-sum/' and filter to those that have both tag observations. "
                    "For the resulting ids, call retrieve_entities to fetch their observations, then return a normalized list of (id, title, 1–2 key points) based on the retrieved entities."
                )
                workflow.logger.info("Querying notes by tags")
                r2 = await Runner.run(
                    starting_agent=agent,
                    input=query_prompt,
                    previous_response_id=r1.last_response_id,
                )

                # Step 3: Synthesis with citations
                synth_prompt = (
                    "Using only the recalled notes, produce a 5-bullet brief. "
                    "Include one citation per bullet in the form '(Note: id)'. Do not introduce new facts."
                )
                workflow.logger.info("Synthesizing brief from recalled notes")
                r3 = await Runner.run(
                    starting_agent=agent,
                    input=synth_prompt,
                    previous_response_id=r2.last_response_id,
                )

                # Step 4: Update and re-query (optional demonstration)
                update_prompt = (
                    "Update the note 'scratchpad/ai-sum/003' to include more precise mitigation:"
                    " 'threshold=0.7; fallback to full email on low confidence'. Then delete the note"
                    " 'scratchpad/ai-sum/005'. Finally, list only the remaining 'risk' notes with (id, updated content)."
                )
                workflow.logger.info(
                    "Updating one note and deleting another, then re-listing risk notes"
                )
                r4 = await Runner.run(
                    starting_agent=agent,
                    input=update_prompt,
                    previous_response_id=r3.last_response_id,
                )

                return (
                    f"WRITE CONFIRMATIONS:\n{r1.final_output}\n\n"
                    f"QUERY RESULTS:\n{r2.final_output}\n\n"
                    f"SYNTHESIS:\n{r3.final_output}\n\n"
                    f"UPDATES:\n{r4.final_output}"
                )
