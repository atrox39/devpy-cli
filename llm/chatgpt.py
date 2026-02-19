import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
  model='gpt-4o-mini',
  api_key=os.getenv('OPENAI_API_KEY'),
  max_tokens=1500,
)
