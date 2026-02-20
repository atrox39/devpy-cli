import os
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
  model='gemini-1.5-pro',
  api_key=os.getenv('GOOGLE_API_KEY'),
  max_output_tokens=1500,
)
