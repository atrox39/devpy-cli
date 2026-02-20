import os
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
  model='claude-3-5-sonnet-latest',
  api_key=os.getenv('ANTHROPIC_API_KEY'),
  max_tokens=1500,
)
