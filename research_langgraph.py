from langgraph.graph import StateGraph,START,END
from typing import TypedDict,Annotated
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode,tools_condition
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage,BaseMessage,SystemMessage
import sqlite3
from dotenv import load_dotenv
from rag import rag_tool,report_tool,search_tool,model_with_tools
load_dotenv()

model = ChatOpenAI(model='gpt-4o-mini')

class AI_ResearchState(TypedDict):
    messages : Annotated[list[BaseMessage],add_messages]

def chatbot(state:AI_ResearchState):
        messages = [
        SystemMessage(
            content="""
You are a PDF Research Assistant.

A PDF is already loaded.

For any question that is not explicitly asking for:
- latest news
- current events
- today's information

you MUST call rag_tool first.

Never use search_tool for:
- project questions
- author names
- document content
- summaries
- explanations of the uploaded PDF

Use search_tool only for current web information.
"""
        )
    ] + state["messages"]
        response = model_with_tools.invoke(messages)
        print("Tool Calls:")
        print("\nTOOL CALLS:")
        print(response.tool_calls)

        return {"messages":[response]}
        

tool_node = ToolNode(
      [rag_tool,report_tool,search_tool]
)
graph = StateGraph(AI_ResearchState)

graph.add_node('chatbot',chatbot)
graph.add_node('tools',tool_node)

graph.add_edge(START,'chatbot')
graph.add_conditional_edges('chatbot',tools_condition)
graph.add_edge('tools','chatbot')

conn = sqlite3.connect(database='project_db',check_same_thread=False)

checkpointer = SqliteSaver(conn=conn)



workflow = graph.compile(checkpointer=checkpointer)
def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    return list(all_threads)




