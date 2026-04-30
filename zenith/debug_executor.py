import asyncio
from config import settings
from core.executor import PlanExecutor

async def main():
    executor = PlanExecutor()
    plan = {
        'type': 'tool_execution',
        'requires_execution': True,
        'template': 'add_task',
        'name': 'Add Task',
        'steps': [{'action': 'tasks.add_task', 'params': {'title': 'Eat lunch'}, 'status': 'pending'}],
        'entities': {}
    }
    
    # Just need mock credentials or fail? We don't have user credentials here.
    # We can just see if it attempts to execute and assess risk.
    print(executor.execute_plan)
    
if __name__ == "__main__":
    asyncio.run(main())
