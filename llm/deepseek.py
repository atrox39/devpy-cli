import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
  model='deepseek-chat',
  api_key=os.getenv('DEEPSEEK_API_KEY'),
  base_url='https://api.deepseek.com/v1',
  max_tokens=1500,
)
