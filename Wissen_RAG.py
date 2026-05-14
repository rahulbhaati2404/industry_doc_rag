# Databricks notebook source
# Force update typing extensions and pydantic to avoid the TypedDict error
%pip install -U typing-extensions pydantic langchain-community pypdf
%pip install databricks-langchain langchain-text-splitters
%pip install databricks-sdk databricks-langchain


# COMMAND ----------

from langchain_community.document_loaders import PyPDFDirectoryLoader

loader = PyPDFDirectoryLoader("/Volumes/workspace/default/rag-pdf")
docs = loader.load()

if docs:
    print("Documents loaded successfully.")
else:
    print("No documents found.")

# COMMAND ----------

from langchain_text_splitters import RecursiveCharacterTextSplitter
import pandas as pd

# Split documents into chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = []
for doc in docs:
    for chunk in text_splitter.split_text(doc.page_content):
        chunks.append({"source": doc.metadata.get("source", ""), "chunk": chunk})

# Create pandas DataFrame
df = pd.DataFrame(chunks)

# Display DataFrame
display(df)

# COMMAND ----------

# Convert pandas DataFrame to Spark DataFrame
spark_df = spark.createDataFrame(df)

# Define table name
table_name = "rag_pdf_chunks"

# Save Spark DataFrame as a table
spark_df.write.mode("overwrite").saveAsTable(table_name)

print(f"Success: Data saved to table '{table_name}'")

# COMMAND ----------

# 1. Fetch data from the Delta Table you just created
# We collect the 'chunk' column specifically
chunks_list = spark.table("workspace.default.rag_pdf_chunks").select("chunk").collect()

# 2. Join all chunks into one large block of text
# Since you have few files, this will easily fit in the LLM's memory (context window)
full_context = "\n\n".join([row.chunk for row in chunks_list])

print(f"Context loaded: {len(chunks_list)} chunks prepared.")

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# List all endpoints and print those starting with 'databricks-'
available_models = [e.name for e in w.serving_endpoints.list() if e.name.startswith("databricks-")]

print("--- COPY ONE OF THESE NAMES ---")
for model in available_models:
    print(model)

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

w = WorkspaceClient()

# Choose a standard 2026 model
# Recommendation: Meta-Llama-3.3-70B-Instruct or Gemini-3.1-Pro
MODEL_NAME = "databricks-gpt-oss-120b"

# Define your question
user_question = "What are numbers of holidays in wissen in this year?"

# Combine context and question into a single prompt
prompt_content = f"""You are a helpful company assistant. Use ONLY the provided context to answer.

Context:
{full_context}

Question: {user_question}
Answer:"""

# Call the model
response = w.serving_endpoints.query(
    name=MODEL_NAME,
    messages=[
        ChatMessage(role=ChatMessageRole.USER, content=prompt_content)
    ]
)

print("\n--- AI ANSWER ---")
print(response.choices[0].message.content)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC # Step-by-step Explanation of Each Notebook Cell
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Cell 1: Install Required Packages
# MAGIC
# MAGIC python
# MAGIC # Force update typing extensions and pydantic to avoid the TypedDict error
# MAGIC %pip install -U typing-extensions pydantic langchain-community pypdf
# MAGIC %pip install databricks-langchain langchain-text-splitters
# MAGIC %pip install databricks-sdk databricks-langchain
# MAGIC
# MAGIC
# MAGIC **What it does:**  
# MAGIC - Installs and updates Python packages needed for document loading, text splitting, and Databricks integration.
# MAGIC - Ensures compatibility and avoids errors (e.g., TypedDict error).
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Cell 2: Load PDF Documents
# MAGIC
# MAGIC python
# MAGIC from langchain_community.document_loaders import PyPDFDirectoryLoader
# MAGIC
# MAGIC loader = PyPDFDirectoryLoader("/Volumes/workspace/default/rag-pdf")
# MAGIC docs = loader.load()
# MAGIC
# MAGIC if docs:
# MAGIC     print("Documents loaded successfully.")
# MAGIC else:
# MAGIC     print("No documents found.")
# MAGIC
# MAGIC
# MAGIC **What it does:**  
# MAGIC - Imports a PDF loader from LangChain.
# MAGIC - Loads all PDFs from a specified directory.
# MAGIC - Checks if documents are loaded and prints a message.
# MAGIC
# MAGIC **Code details:**  
# MAGIC - `PyPDFDirectoryLoader` reads all PDF files in the folder.
# MAGIC - `loader.load()` returns a list of document objects.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Cell 3: Split Documents into Chunks
# MAGIC
# MAGIC python
# MAGIC from langchain_text_splitters import RecursiveCharacterTextSplitter
# MAGIC import pandas as pd
# MAGIC
# MAGIC # Split documents into chunks
# MAGIC text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
# MAGIC chunks = []
# MAGIC for doc in docs:
# MAGIC     for chunk in text_splitter.split_text(doc.page_content):
# MAGIC         chunks.append({"source": doc.metadata.get("source", ""), "chunk": chunk})
# MAGIC
# MAGIC # Create pandas DataFrame
# MAGIC df = pd.DataFrame(chunks)
# MAGIC
# MAGIC # Display DataFrame
# MAGIC display(df)
# MAGIC
# MAGIC
# MAGIC **What it does:**  
# MAGIC - Splits each document's text into smaller chunks for easier processing.
# MAGIC - Stores chunks and their source in a pandas DataFrame.
# MAGIC
# MAGIC **Code details:**  
# MAGIC - `RecursiveCharacterTextSplitter` splits text into chunks of 1000 characters, overlapping by 200.
# MAGIC - Each chunk is stored with its source metadata.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Cell 4: Save Chunks to Delta Table
# MAGIC
# MAGIC python
# MAGIC # Convert pandas DataFrame to Spark DataFrame
# MAGIC spark_df = spark.createDataFrame(df)
# MAGIC
# MAGIC # Define table name
# MAGIC table_name = "rag_pdf_chunks"
# MAGIC
# MAGIC # Save Spark DataFrame as a table
# MAGIC spark_df.write.mode("overwrite").saveAsTable(table_name)
# MAGIC
# MAGIC print(f"Success: Data saved to table '{table_name}'")
# MAGIC
# MAGIC
# MAGIC **What it does:**  
# MAGIC - Converts the pandas DataFrame to a Spark DataFrame.
# MAGIC - Saves the chunks as a Delta table in Databricks.
# MAGIC
# MAGIC **Code details:**  
# MAGIC - `spark.createDataFrame(df)` creates a Spark DataFrame.
# MAGIC - `saveAsTable` writes the DataFrame to a table, overwriting any existing data.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Cell 5: Prepare Context for LLM
# MAGIC
# MAGIC python
# MAGIC # 1. Fetch data from the Delta Table you just created
# MAGIC # We collect the 'chunk' column specifically
# MAGIC chunks_list = spark.table("workspace.default.rag_pdf_chunks").select("chunk").collect()
# MAGIC
# MAGIC # 2. Join all chunks into one large block of text
# MAGIC # Since you have few files, this will easily fit in the LLM's memory (context window)
# MAGIC full_context = "\n\n".join([row.chunk for row in chunks_list])
# MAGIC
# MAGIC print(f"Context loaded: {len(chunks_list)} chunks prepared.")
# MAGIC
# MAGIC
# MAGIC **What it does:**  
# MAGIC - Reads the chunks from the Delta table.
# MAGIC - Joins all chunks into a single string to use as context for the language model.
# MAGIC
# MAGIC **Code details:**  
# MAGIC - `spark.table(...).select("chunk").collect()` fetches all chunk texts.
# MAGIC - `"\n\n".join([...])` combines them into one block.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Cell 6: List Available LLM Endpoints
# MAGIC
# MAGIC python
# MAGIC from databricks.sdk import WorkspaceClient
# MAGIC
# MAGIC w = WorkspaceClient()
# MAGIC
# MAGIC # List all endpoints and print those starting with 'databricks-'
# MAGIC available_models = [e.name for e in w.serving_endpoints.list() if e.name.startswith("databricks-")]
# MAGIC
# MAGIC print("--- COPY ONE OF THESE NAMES ---")
# MAGIC for model in available_models:
# MAGIC     print(model)
# MAGIC
# MAGIC
# MAGIC **What it does:**  
# MAGIC - Lists all available Databricks model endpoints for inference.
# MAGIC - Prints names of endpoints starting with "databricks-".
# MAGIC
# MAGIC **Code details:**  
# MAGIC - `WorkspaceClient()` connects to Databricks workspace.
# MAGIC - `w.serving_endpoints.list()` gets all endpoints.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Cell 7: Query LLM with Context and Question
# MAGIC
# MAGIC python
# MAGIC from databricks.sdk import WorkspaceClient
# MAGIC from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
# MAGIC
# MAGIC w = WorkspaceClient()
# MAGIC
# MAGIC # Choose a standard 2026 model
# MAGIC # Recommendation: Meta-Llama-3.3-70B-Instruct or Gemini-3.1-Pro
# MAGIC MODEL_NAME = "databricks-gpt-oss-120b"
# MAGIC
# MAGIC # Define your question
# MAGIC user_question = "What are numbers of holidays in wissen in this year?"
# MAGIC
# MAGIC # Combine context and question into a single prompt
# MAGIC prompt_content = f"""You are a helpful company assistant. Use ONLY the provided context to answer.
# MAGIC
# MAGIC Context:
# MAGIC {full_context}
# MAGIC
# MAGIC Question: {user_question}
# MAGIC Answer:"""
# MAGIC
# MAGIC # Call the model
# MAGIC response = w.serving_endpoints.query(
# MAGIC     name=MODEL_NAME,
# MAGIC     messages=[
# MAGIC         ChatMessage(role=ChatMessageRole.USER, content=prompt_content)
# MAGIC     ]
# MAGIC )
# MAGIC
# MAGIC print("\n--- AI ANSWER ---")
# MAGIC print(response.choices[0].message.content)
# MAGIC
# MAGIC
# MAGIC **What it does:**  
# MAGIC - Sends the combined context and user question to a Databricks LLM endpoint.
# MAGIC - Prints the model's answer.
# MAGIC
# MAGIC **Code details:**  
# MAGIC - `ChatMessage` structures the prompt for the LLM.
# MAGIC - `w.serving_endpoints.query(...)` sends the prompt and receives the answer.
# MAGIC
# MAGIC ---