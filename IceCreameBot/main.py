import asyncio

from dotenv import load_dotenv
from MainChef.agent import MainChef  
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from utils import  call_agent_async

from CRUD.db import initialize_db_pool, close_db_pool

load_dotenv()

initial_state = {
    "username" : "",
    "customer_id": None,
    "telepone_number" : "",
    "address" : "",
    "mood" : "",
    "age"  : None,
    "table" : "",
    "order_id" : None,
    "order" : [],
    "discount" : None,
    "special_discount" : {},
    "type" : "",
    "amount" : 0,
}

session_service = InMemorySessionService()


async def main_async():
    
    initialize_db_pool()
    
    APP_NAME = "Main Chef MoodScoope"
    USER_ID = "aiwithsuli"

    new_session = session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state=initial_state,
    )
    SESSION_ID = new_session.id
    print(f"Created new session: {SESSION_ID}")

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

    close_db_pool()

def main():
    """Entry point for the application."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()