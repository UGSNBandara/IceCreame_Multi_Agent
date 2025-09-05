import asyncio

from dotenv import load_dotenv
from MainChef.agent import MainChef  
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from utils import  call_agent_async

from CRUD.icecreamCrud import fetch_ice_creams, fetch_categories
from Cache.IceCreamCache import catalog_cache

load_dotenv()

initial_state = {
    "customer_name" : None,
    "customer_id": None,
    "phone_number" : None,
    "address" : None,
    "mood" : None,
    "age_group"  : None,
    "table_number" : None,
    "order_id" : None,
    "order_type" : "",
}

session_service = InMemorySessionService()


async def main_async():
    
    ices = await fetch_ice_creams()
    cats = await fetch_categories()
    catalog_cache.load(ices, cats)
    
    APP_NAME = "Main Chef MoodScoope"
    USER_ID = "aiwithsuli"

    new_session = session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state=initial_state,
    )
    
    SESSION_ID = new_session.id
    print(f"Created new session: {SESSION_ID}")

    new_session.state["session_id"] = SESSION_ID
    
    runner = Runner(
        agent=MainChef,
        app_name=APP_NAME,
        session_service=session_service,
    )
    
    print("\nWelcome to Customer Service Chat!")
    print("Type 'exit' or 'quit' to end the conversation.\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            print("Ending conversation. Goodbye!")
            break

        await call_agent_async(runner, USER_ID, SESSION_ID, user_input)

    final_session = session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    print("\nFinal Session State:")
    for key, value in final_session.state.items():
        print(f"{key}: {value}")

def main():
    """Entry point for the application."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()