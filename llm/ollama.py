import os
from langchain_openai import ChatOpenAI


def _get_base_url() -> str:
  base = os.getenv('LLM_BASE_URL') or os.getenv('OLLAMA_BASE_URL') or os.getenv('OPENWEBUI_BASE_URL')
  if base:
    base = base.rstrip('/')
    if not base.endswith('/v1'):
      base = base + '/v1'
    return base
  return 'http://localhost:11434/v1'


llm = ChatOpenAI(
  model=os.getenv('OLLAMA_MODEL', 'llama3.1:8b'),
  api_key=os.getenv('OPENAI_API_KEY', 'ollama'),
  base_url=_get_base_url(),
  max_tokens=1500,
)
