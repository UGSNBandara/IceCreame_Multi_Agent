from google.adk.agents import Agent


Marketer = Agent (
    name="Marketer",
    model="gemini-2.0-flash",
    description="Agent who handle the Marketing part",
    instruction="""
    You are the marketing agent of moodscoope ice cream shop. You have to help the cutomer to select ice creames and promote the ice creams and suggest ice cremas for cutomer 
    based on their history and current time, thier mood and age.
    
    
    
    """
)
