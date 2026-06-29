from langchain_openai import ChatOpenAI,OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import PromptTemplate
from langchain_community.tools import DuckDuckGoSearchRun
import os

from langchain.tools import tool
from dotenv import load_dotenv
load_dotenv()
model = ChatOpenAI(model='gpt-4o-mini',temperature=0)

prompt = PromptTemplate(
    template="""
    you are helpfull assistant ,
    give answers based on only context
If the answer is not present in the context,
respond with exactly:

NOT FOUND
context:{context}
question:{question}
""",
input_variables=['question','context']
)

report_prompt = PromptTemplate(
    template="""
You are a research analyst.
Generate a report using EXACTLY the following structure.

# Executive Summary

# Key Findings

# Important Concepts

# Recommendations

# Conclusion

Do not use any other headings.
Do not change the heading names.
context:{context}
""",
input_variables=['context']
)


def create_vector_store(pdf_path):
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    

    splitter = RecursiveCharacterTextSplitter(chunk_size = 1000,chunk_overlap = 300)
    chunks = splitter.split_documents(documents=documents)

    embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

    vector_store = Chroma.from_documents(
    embedding=embeddings,
    documents=chunks,
    persist_directory="vector_store"
)
    retriever = vector_store.as_retriever(
        search_type = 'mmr',
        search_kwargs={'k':10}
    )
    return retriever


def doc_format(docs):
    context_text = "\n\n".join(doc.page_content for doc in docs)
    return context_text

def get_answer(question):
    if retriever is None:
        return "please upload pdf first "
    print("Searching documents...")
    docs = retriever.invoke(question)
    print("\n===== RETRIEVED DOCS =====")

    for i, doc in enumerate(docs):
        print(f"\nDOC {i+1}")
        print(doc.metadata)
        print(doc.page_content[:500])

    print("==========================")
    context = doc_format(docs)
    final_prompt = prompt.invoke({
        'question':question,
        'context':context
    })
    print("Sending to GPT...")
    response = model.invoke(final_prompt)

    return response.content

def generate_report():
    if retriever is None:
        return "please upload pdf first "
    docs = retriever.invoke(
        """
summarize or generate report of entire document
"""
    )
    
    chunk_summaries = []

    for doc in docs:

        chunk_prompt = f"""
Summarize the following document chunk.

Chunk:
{doc.page_content}

Return only the summary.
"""
        summary = model.invoke(chunk_prompt)
        chunk_summaries.append(summary.content)

    combined_summary = "\n\n".join(chunk_summaries)

    final_prompt = report_prompt.invoke({
        'context':combined_summary
        })
    response = model.invoke(final_prompt)
    return response.content

search = DuckDuckGoSearchRun()

#tool-1
@tool
def rag_tool(question:str):
    """
    Answer questions from the uploaded PDF.

    Use this tool whenever the user asks:
    - about the uploaded PDF
    - summarize the PDF
    - explain the document
    - tell me about this PDF
    - what does the document say
    - questions whose answers should come from the uploaded PDF

    The PDF has already been loaded into the system.
    """
    return get_answer(question)

#tool-2
@tool
def report_tool(question:str):
    """
    Generate a complete report from the uploaded PDF.

    Use this tool whenever the user asks:
    - generate report
    - summarize document
    - report on document
    - summarize PDF
    - document overview

    The PDF is already loaded in the system.
    """
    return generate_report()
#tool-3
@tool
def search_tool(query:str):
    """
     Use ONLY for:
    - latest news
    - current events
    - today's information
    - recent updates

    Do NOT use for:
    - uploaded PDF
    - project questions
    - document content
    - author names
    - report generation
    """
    return search.run(query)
tools = [rag_tool,report_tool,search_tool]
model_with_tools = model.bind_tools(tools)

retriever = None
def load_pdf(pdf_path):
    global retriever
    print("PDF LOADING STARTED")
    retriever = create_vector_store(pdf_path)
    print("PDF LOADING COMPLETED")


