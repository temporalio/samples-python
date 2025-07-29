#!/usr/bin/env python3
"""
Setup script to create vector store with sample documents for testing FileSearchWorkflow.
Creates documents about Arrakis/Dune and uploads them to OpenAI for file search testing.
"""

import asyncio
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List

from openai import AsyncOpenAI

# Sample knowledge base content
KNOWLEDGE_BASE = {
    "arrakis_overview": """
Arrakis: The Desert Planet

Arrakis, also known as Dune, is the third planet of the Canopus system. This harsh desert world is the sole source of the spice melange, the most valuable substance in the known universe.

Key characteristics:
- Single biome: Desert covering the entire planet
- No natural precipitation
- Extreme temperature variations between day and night
- Home to the giant sandworms (Shai-Hulud)
- Indigenous population: the Fremen

The planet's ecology is entirely dependent on the sandworms, which produce the spice as a byproduct of their life cycle. Water is incredibly scarce, leading to the development of stillsuits and other water conservation technologies.
""",
    "spice_melange": """
The Spice Melange

Melange, commonly known as "the spice," is the most important substance in the Dune universe. This geriatric spice extends life, expands consciousness, and is essential for space navigation.

Properties of Spice:
- Extends human lifespan significantly
- Enhances mental abilities and prescient vision
- Required for Guild Navigators to fold space
- Highly addictive with fatal withdrawal symptoms
- Turns eyes blue over time (the "Eyes of Ibad")

Production:
The spice is created through the interaction of sandworms with pre-spice masses in the deep desert. The presence of water is toxic to sandworms, making Arrakis the only known source of spice in the universe.

Economic Impact:
Control of spice production grants immense political and economic power, making Arrakis the most strategically important planet in the Imperium.
""",
    "sandworms": """
Sandworms of Arrakis

The sandworms, known to the Fremen as Shai-Hulud ("Old Man of the Desert"), are colossal creatures that dominate Arrakis. These massive beings can grow to lengths of over 400 meters and live for thousands of years.

Characteristics:
- Enormous size: up to 400+ meters in length
- Extreme sensitivity to water and moisture
- Produce the spice melange as part of their life cycle
- Territorial and attracted to rhythmic vibrations
- Crystalline teeth capable of crushing rock and metal

Life Cycle:
Sandworms begin as sandtrout, small creatures that sequester water. They eventually metamorphose into the giant sandworms through a complex process involving spice production.

Cultural Significance:
The Fremen worship sandworms as semi-divine beings and have developed elaborate rituals around them, including the dangerous practice of sandworm riding.
""",
    "fremen_culture": """
The Fremen of Arrakis

The Fremen are the indigenous people of Arrakis, perfectly adapted to life in the harsh desert environment. Their culture revolves around water conservation, survival, and reverence for the sandworms.

Cultural Practices:
- Water discipline: Every drop of moisture is preserved
- Stillsuits: Advanced technology to recycle body moisture
- Desert survival skills passed down through generations
- Ritualistic relationship with sandworms
- Sietch communities: Hidden underground settlements

Religious Beliefs:
The Fremen follow a syncretic religion combining elements of Islam, Buddhism, and Christianity, adapted to their desert environment. They believe in prophecies of a messiah who will transform Arrakis.

Military Prowess:
Despite their seemingly primitive lifestyle, the Fremen are formidable warriors, using their intimate knowledge of the desert and unconventional tactics to great effect.
""",
    "house_atreides": """
House Atreides and Arrakis

House Atreides, led by Duke Leto Atreides, was granted control of Arrakis by Emperor Shaddam IV in a political trap designed to destroy the noble house. This transition from House Harkonnen marked the beginning of the events in Dune.

Key Figures:
- Duke Leto Atreides: Noble leader focused on honor and justice
- Lady Jessica: Bene Gesserit concubine and mother of Paul
- Paul Atreides: Heir to the duchy and potential Kwisatz Haderach
- Duncan Idaho: Loyal swordmaster and warrior
- Gurney Halleck: Weapons master and troubadour

The Atreides approach to ruling Arrakis differed dramatically from the Harkonnens, seeking to work with the Fremen rather than exploit them. This philosophy, while noble, ultimately led to their downfall when the Emperor and Harkonnens betrayed them.

Legacy:
Though House Atreides was destroyed in the coup, Paul's survival and alliance with the Fremen would eventually lead to an even greater destiny.
""",
    "ecology_arrakis": """
The Ecology of Arrakis

Arrakis presents a unique ecosystem entirely based on the water cycle created by sandworms and sandtrout. This closed ecological system has evolved over millennia to support life in extreme desert conditions.

Water Cycle:
- Sandtrout sequester all available water deep underground
- This creates the desert conditions necessary for spice production
- Adult sandworms are killed by water, maintaining the cycle
- Plants and animals have evolved extreme water conservation

Flora and Fauna:
- Desert plants with deep root systems and water storage
- Small desert animals adapted to minimal water consumption
- No large surface water bodies exist naturally
- All life forms show evolutionary adaptation to water scarcity

The ecosystem is incredibly fragile - any significant introduction of water could disrupt the entire balance and potentially eliminate spice production, fundamentally changing the planet and the universe's economy.
""",
}


@asynccontextmanager
async def temporary_files(content_dict: Dict[str, str]):
    """Context manager to create and cleanup temporary files."""
    temp_files = []
    try:
        for name, content in content_dict.items():
            temp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", prefix=f"{name}_", delete=False
            )
            temp_file.write(content)
            temp_file.close()
            temp_files.append((name, temp_file.name))

        yield temp_files
    finally:
        for _, temp_path in temp_files:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


async def upload_files_to_openai(temp_files: List[tuple[str, str]]) -> List[str]:
    """Upload temporary files to OpenAI and return file IDs."""
    client = AsyncOpenAI()
    file_ids = []

    for name, temp_path in temp_files:
        try:
            with open(temp_path, "rb") as f:
                file_obj = await client.files.create(file=f, purpose="assistants")
                file_ids.append(file_obj.id)
                print(f"Uploaded {name}: {file_obj.id}")
        except Exception as e:
            print(f"Error uploading {name}: {e}")

    return file_ids


async def create_vector_store_with_assistant(file_ids: List[str]) -> str:
    """Create an assistant with vector store containing the uploaded files."""
    client = AsyncOpenAI()

    try:
        assistant = await client.beta.assistants.create(
            name="Arrakis Knowledge Assistant",
            instructions="You are an expert on Arrakis and the Dune universe. Use the uploaded files to answer questions about the desert planet, spice, sandworms, Fremen culture, and related topics.",
            model="gpt-4o",
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_stores": [
                        {
                            "file_ids": file_ids,
                            "metadata": {"name": "Arrakis Knowledge Base"},
                        }
                    ]
                }
            },
        )

        # Extract vector store ID from assistant
        if assistant.tool_resources and assistant.tool_resources.file_search:
            vector_store_ids = assistant.tool_resources.file_search.vector_store_ids
            if vector_store_ids:
                return vector_store_ids[0]

        raise Exception("No vector store ID found in assistant response")

    except Exception as e:
        print(f"Error creating assistant: {e}")
        raise


def update_workflow_files(vector_store_id: str):
    """Update workflow files with the new vector store ID."""
    import re

    files_to_update = ["run_file_search_workflow.py"]

    # Pattern to match any vector store ID with the specific comment
    pattern = r'(vs_[a-f0-9]+)",\s*#\s*Vector store with Arrakis knowledge'
    replacement = f'{vector_store_id}",  # Vector store with Arrakis knowledge'

    for filename in files_to_update:
        file_path = Path(__file__).parent / filename
        if file_path.exists():
            try:
                content = file_path.read_text()
                if re.search(pattern, content):
                    updated_content = re.sub(pattern, replacement, content)
                    file_path.write_text(updated_content)
                    print(f"Updated {filename} with vector store ID")
                else:
                    print(f"No matching pattern found in {filename}")
            except Exception as e:
                print(f"Error updating {filename}: {e}")


async def main():
    """Main function to set up the knowledge base."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return

    print("Setting up Arrakis knowledge base...")

    try:
        # Create temporary files and upload them
        async with temporary_files(KNOWLEDGE_BASE) as temp_files:
            print(f"Created {len(temp_files)} temporary files")

            file_ids = await upload_files_to_openai(temp_files)

            if not file_ids:
                print("Error: No files were successfully uploaded")
                return

            print(f"Successfully uploaded {len(file_ids)} files")

            # Create vector store via assistant
            vector_store_id = await create_vector_store_with_assistant(file_ids)

            print(f"Created vector store: {vector_store_id}")

            # Update workflow files
            update_workflow_files(vector_store_id)

            print()
            print("=" * 60)
            print("KNOWLEDGE BASE SETUP COMPLETE")
            print("=" * 60)
            print(f"Vector Store ID: {vector_store_id}")
            print(f"Files indexed: {len(file_ids)}")
            print("Content: Arrakis/Dune universe knowledge")
            print("=" * 60)

    except Exception as e:
        print(f"Setup failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
