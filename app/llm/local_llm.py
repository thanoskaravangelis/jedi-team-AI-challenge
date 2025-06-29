"""Local LLM client for LM Studio running Qwen2.5-7b-instruct."""

import os
import requests
from typing import Optional, List, Dict, Any
from langchain.llms.base import LLM
from langchain.schema import Generation, LLMResult
from langchain.callbacks.manager import CallbackManagerForLLMRun
from pydantic import Field
import logging

logger = logging.getLogger(__name__)


class LocalLMStudioLLM(LLM):
    """Custom LLM client for LM Studio local models."""
    
    base_url: str = Field(default="http://127.0.0.1:1234")
    model_name: str = Field(default="qwen2.5-7b-instruct")
    temperature: float = Field(default=0.1)
    max_tokens: int = Field(default=1500)
    timeout: int = Field(default=30)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = kwargs.get('base_url', os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:1234"))
        self.model_name = kwargs.get('model_name', "qwen2.5-7b-instruct")
        self.temperature = kwargs.get('temperature', 0.1)
        self.max_tokens = kwargs.get('max_tokens', 1500)
        self.timeout = kwargs.get('timeout', 30)
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to LM Studio."""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json()
                logger.info(f"✅ Connected to LM Studio at {self.base_url}")
                logger.info(f"📋 Available models: {[m.get('id', 'unknown') for m in models.get('data', [])]}")
            else:
                logger.warning(f"⚠️ LM Studio responded with status {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Could not connect to LM Studio at {self.base_url}: {e}")
    
    @property
    def _llm_type(self) -> str:
        """Return identifier of llm."""
        return "local_lm_studio"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the LM Studio model."""
        try:
            # Enhanced system prompt for better ReAct format compliance
            system_prompt = """You are a helpful AI assistant that follows instructions precisely. When given a prompt that requires a specific format (like Action/Thought patterns), follow that format exactly. Always be concise and precise in your responses."""
            
            # Prepare the request payload (OpenAI-compatible format)
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": kwargs.get('temperature', self.temperature),
                "max_tokens": kwargs.get('max_tokens', self.max_tokens),
                "stream": False,
                "stop": stop or ["Observation:", "\n\nQuestion:"]  # Better stop sequences for ReAct
            }
            
            # Make request to LM Studio
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not content:
                    logger.warning("Empty response from LM Studio")
                    return "I apologize, but I couldn't generate a proper response. Please try again."
                
                logger.debug(f"LM Studio response: {content[:100]}...")
                return content.strip()  # Strip whitespace for cleaner output
            else:
                logger.error(f"LM Studio API error: {response.status_code} - {response.text}")
                return f"Error: LM Studio API returned status {response.status_code}"
                
        except requests.exceptions.Timeout:
            logger.error("LM Studio request timed out")
            return "Error: Request to local LM Studio timed out. Please check if the service is running."
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to LM Studio at {self.base_url}")
            return f"Error: Could not connect to LM Studio at {self.base_url}. Please ensure LM Studio is running."
        except Exception as e:
            logger.error(f"Unexpected error calling LM Studio: {e}")
            return f"Error: Unexpected error occurred: {str(e)}"
    
    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Generate responses for multiple prompts."""
        generations = []
        
        for prompt in prompts:
            response = self._call(prompt, stop, run_manager, **kwargs)
            generations.append([Generation(text=response)])
        
        return LLMResult(generations=generations)


def create_local_llm(
    base_url: Optional[str] = None,
    model_name: str = "qwen2.5-7b-instruct", 
    temperature: float = 0.1,
    max_tokens: int = 1500,
    **kwargs
) -> LocalLMStudioLLM:
    """Create a Local LM Studio LLM instance."""
    
    base_url = base_url or os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:1234")
    
    return LocalLMStudioLLM(
        base_url=base_url,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
