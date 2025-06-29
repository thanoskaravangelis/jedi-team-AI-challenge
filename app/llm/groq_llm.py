"""Custom Groq LLM wrapper for LangChain compatibility."""

import os
from typing import Any, List, Optional, Iterator
from langchain_core.language_models.llms import LLM
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from pydantic import Field
import logging

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

logger = logging.getLogger(__name__)


class GroqChatModel(BaseChatModel):
    """Custom Groq chat model wrapper for LangChain."""
    
    # Properly define Pydantic fields
    api_key: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    model: str = Field(default="qwen/qwen3-32b") #"llama3-8b-8192"
    temperature: float = Field(default=0.1)
    max_tokens: int = Field(default=2000)
    _client: Optional[Groq] = Field(default=None, exclude=True)  # Private field, excluded from serialization
    
    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True  # Allow private attributes
    
    def __init__(self, **kwargs):
        if not GROQ_AVAILABLE:
            raise ImportError("groq package not installed. Install with: pip install groq")
        
        super().__init__(**kwargs)
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        # Initialize Groq client after parent initialization
        try:
            self._client = Groq(api_key=self.api_key)
            logger.info(f"✅ Groq client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Groq client: {e}")
            raise
    
    @property
    def client(self) -> Groq:
        """Get the Groq client."""
        if self._client is None:
            self._client = Groq(api_key=self.api_key)
        return self._client
    
    @property
    def _llm_type(self) -> str:
        """Return identifier of the LLM."""
        return "groq"
    
    def _convert_messages_to_groq_format(self, messages: List[BaseMessage]) -> List[dict]:
        """Convert LangChain messages to Groq format."""
        groq_messages = []
        
        for message in messages:
            if isinstance(message, HumanMessage):
                groq_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                groq_messages.append({"role": "assistant", "content": message.content})
            elif isinstance(message, SystemMessage):
                groq_messages.append({"role": "system", "content": message.content})
            else:
                # For any other message type, treat as user message
                groq_messages.append({"role": "user", "content": str(message.content)})
        
        return groq_messages
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a response from Groq."""
        
        try:
            # Convert messages to Groq format
            groq_messages = self._convert_messages_to_groq_format(messages)
            
            # Prepare request parameters
            request_params = {
                "model": self.model,
                "messages": groq_messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            
            # Add stop sequences if provided
            if stop:
                request_params["stop"] = stop
            
            # Make the API call
            response = self.client.chat.completions.create(**request_params)
            
            # Extract the content
            content = response.choices[0].message.content
            
            # Create the response
            message = AIMessage(content=content)
            generation = ChatGeneration(message=message)
            
            return ChatResult(generations=[generation])
            
        except Exception as e:
            logger.error(f"❌ Error calling Groq API: {e}")
            # Return a fallback response
            error_message = f"Error calling Groq API: {str(e)}"
            message = AIMessage(content=error_message)
            generation = ChatGeneration(message=message)
            return ChatResult(generations=[generation])
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async version - for now, just call the sync version."""
        return self._generate(messages, stop, run_manager, **kwargs)


def create_groq_llm(
    api_key: Optional[str] = None,
    model: str = "qwen/qwen3-32b",
    temperature: float = 0.1,
    max_tokens: int = 2000,
) -> GroqChatModel:
    """Factory function to create a Groq LLM instance."""
    kwargs = {
        'model': model,
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    if api_key:
        kwargs['api_key'] = api_key
    
    return GroqChatModel(**kwargs)
