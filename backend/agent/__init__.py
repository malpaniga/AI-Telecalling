# agent package
# backend.agent.llm is imported lazily in model_test_service — no eager imports here
# to avoid groq/langchain import-time failures in test environments without credentials.
