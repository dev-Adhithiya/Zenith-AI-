import asyncio
from config import settings
from agents.decomposer import DecomposerAgent
from agents.vertex_ai import VertexAIClient

async def main():
    client = VertexAIClient()
    decomposer = DecomposerAgent(client)
    
    context = {
        "intent": {
            "category": "B",
            "intent": "add_task",
            "requires_tools": ["tasks"],
        },
        "entities": {
            "task_descriptions": ["Eat lunch"],
            "dates": ["2026-11-28"],
            "times": ["13:00"]
        },
        "resolved_message": "just eat lunch tmrw at 1pm for one time"
    }
    
    plan = await decomposer.decompose(context)
    print("PLAN:", plan)

if __name__ == "__main__":
    asyncio.run(main())
