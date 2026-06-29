import streamlit as st
from research_langgraph import workflow,retrieve_all_threads
from langchain_core.messages import HumanMessage
import uuid
import rag
import os




st.set_page_config(
    page_title='AI Research Assistant',
    layout='wide'
)

def generate_thread_id():
    thread_id = uuid.uuid4()
    return str(thread_id)

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)  

def load_conversation(thread_id):
    state = workflow.get_state(
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )
    return state.values.get("messages", [])



if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()   

if'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retrieve_all_threads()  
add_thread(st.session_state['thread_id'])      


config = {"configurable":{"thread_id":st.session_state['thread_id']}}

st.sidebar.title("AI Research Assistant")

uploaded_file = st.file_uploader(
    "upload pdf",
    type=["pdf"]
)


if uploaded_file is not None:

    if (
        "current_pdf" not in st.session_state
        or st.session_state["current_pdf"] != uploaded_file.name
    ):

        os.makedirs("uploads", exist_ok=True)

        pdf_path = os.path.join(
            "uploads",
            uploaded_file.name
        )

        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        rag.load_pdf(pdf_path)

        st.session_state["pdf_path"] = pdf_path
        st.session_state["current_pdf"] = uploaded_file.name

        st.success(f"Loaded PDF: {uploaded_file.name}")

if  st.sidebar.button("new chat"):
    reset_chat()
    st.rerun()    

st.sidebar.header("my conversation")

for thread_id in st.session_state['chat_threads'][::-1]:
    if st.sidebar.button(str(thread_id)):
        st.session_state['thread_id'] = thread_id
        messages = load_conversation(thread_id)

        temp_message = []
        for message in messages:
            if isinstance(message,HumanMessage):
                role='user'
            else:
                role='assistant'
            temp_message.append({'role':role,'content':message.content}) 
        st.session_state['message_history']  = temp_message           

for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content']) 

if "pdf_path" in st.session_state:

    import rag

    if rag.retriever is None:

        rag.load_pdf(
            st.session_state["pdf_path"]
        )          

user_input = st.chat_input("type here ")

if user_input:
    st.session_state['message_history'].append({'role':'user','content':user_input})
    with st.chat_message('user'):
        st.write(user_input)

    
    with st.chat_message('assistant'):
        with st.spinner("thinking.."):
            ai_message = st.write_stream(
                message_chunk.content for message_chunk,metadata in workflow.stream(
                    {'messages': [HumanMessage(content=user_input)]},
                    config={"configurable":{"thread_id":st.session_state['thread_id']}},
                    stream_mode='messages'
            

            )
        )
            st.session_state['message_history'].append({'role':'assistant','content':ai_message}) 