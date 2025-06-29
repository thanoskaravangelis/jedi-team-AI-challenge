"""
Answer Quality Evaluator Tool for the Jedi Agent
This tool evaluates agent responses for quality and relevance.
"""

import os
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
from app.llm.groq_llm import create_groq_llm
from app.llm.local_llm import create_local_llm

logger = logging.getLogger(__name__)

# Only import OpenAI if available
try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available for evaluation")


def get_evaluator_llm():
    """Get an LLM instance for evaluation (separate from main agent)."""
    try:
        # Use the same logic as the main agent but create a separate instance
        local_llm_url = os.getenv("LOCAL_LLM_BASE_URL")
        groq_api_key = os.getenv("GROQ_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if local_llm_url:
            logger.info("🏠 Initializing Local LLM for evaluation")
            try:
                return create_local_llm(
                    base_url=local_llm_url,
                    model_name="qwen2.5-7b-instruct",
                    temperature=0.0,  # More deterministic for evaluation
                    max_tokens=1000
                )
            except Exception as e:
                logger.warning(f"Local LLM failed for evaluation: {e}")
                # Fall back to Groq
                
        if groq_api_key and groq_api_key != "YOUR_GROQ_API_KEY_HERE":
            logger.info("🦙 Using Groq LLM for evaluation")
            return create_groq_llm(
                api_key=groq_api_key,
                model="llama3-8b-8192",
                temperature=0.0,  # More deterministic for evaluation
                max_tokens=1000
            )
            
        if openai_api_key and OPENAI_AVAILABLE:
            logger.info("🤖 Using OpenAI for evaluation")
            return ChatOpenAI(
                api_key=openai_api_key,
                model="gpt-4o-mini",
                temperature=0.0,  # More deterministic for evaluation
                max_tokens=1000
            )
            
        # Fallback: create a dummy evaluator that always returns neutral scores
        logger.warning("No LLM available for evaluation - using fallback")
        return None
        
    except Exception as e:
        logger.error(f"Error initializing evaluator LLM: {e}")
        return None


class EvaluatorInput(BaseModel):
    """Input schema for the evaluator tool."""
    query: str = Field(description="The original user query")
    response: str = Field(description="The agent's response to evaluate")
    context: str = Field(default="", description="Additional context about the response")


class AnswerEvaluatorTool(BaseTool):
    """Tool to evaluate the quality of agent responses."""
    
    name = "answer_evaluator"
    description = """Evaluate the quality of an agent response for relevance, accuracy, and completeness.
    This tool provides scores on a 1-5 scale for each dimension."""
    args_schema = EvaluatorInput
    llm: Any = None  # Add this field to the Pydantic model
    
    def __init__(self):
        super().__init__()
        self.llm = get_evaluator_llm()
    
    def _run(self, query: str, response: str, context: str = "") -> str:
        """
        Evaluate the agent response quality.
        
        Args:
            query: The original user query
            response: The agent's response to evaluate
            context: Additional context about the response
            
        Returns:
            JSON string with evaluation scores
        """
        try:
            # Check if LLM is available
            if self.llm is None:
                logger.warning("No LLM available for evaluation - using fallback scores")
                fallback_evaluation = {
                    "relevance_score": 3,
                    "accuracy_score": 3,
                    "completeness_score": 3,
                    "overall_score": 3,
                    "detailed_feedback": "Evaluation unavailable - LLM not initialized",
                    "strengths": ["Response provided"],
                    "areas_for_improvement": ["Enable LLM for detailed evaluation"]
                }
                import json
                return json.dumps(fallback_evaluation)
            
            evaluation_prompt = f"""
You are an expert evaluator assessing the quality of AI assistant responses for market research queries.

ORIGINAL QUERY: {query}

AGENT RESPONSE: {response}

CONTEXT: {context}

Please evaluate this response on the following dimensions using a 1-5 scale:

1. RELEVANCE (1-5): How well does the response address the specific query?
   - 1: Completely off-topic or irrelevant
   - 2: Partially relevant but misses key aspects
   - 3: Generally relevant with some gaps
   - 4: Highly relevant with minor gaps
   - 5: Perfectly addresses all aspects of the query

2. ACCURACY (1-5): How accurate and factual is the information provided?
   - 1: Contains significant errors or misinformation
   - 2: Some inaccuracies or questionable claims
   - 3: Generally accurate with minor issues
   - 4: Highly accurate with well-supported claims
   - 5: Completely accurate with authoritative sources

3. COMPLETENESS (1-5): How comprehensive is the response?
   - 1: Very incomplete, missing critical information
   - 2: Lacks important details or context
   - 3: Covers main points but could be more thorough
   - 4: Comprehensive with minor gaps
   - 5: Thoroughly comprehensive and detailed

4. OVERALL QUALITY (1-5): Overall assessment of response quality
   - 1: Poor quality, not helpful
   - 2: Below average, limited value
   - 3: Average quality, somewhat helpful
   - 4: High quality, very helpful
   - 5: Excellent quality, exceptionally helpful

Provide your evaluation in the following JSON format:
{{
    "relevance_score": X,
    "accuracy_score": X,
    "completeness_score": X,
    "overall_score": X,
    "detailed_feedback": "Brief explanation of your assessment",
    "strengths": ["strength1", "strength2"],
    "areas_for_improvement": ["improvement1", "improvement2"]
}}

Be objective and constructive in your evaluation.
"""

            # Get evaluation from LLM
            evaluation_result = self.llm.invoke(evaluation_prompt)
            
            if hasattr(evaluation_result, 'content'):
                result = evaluation_result.content
            else:
                result = str(evaluation_result)
            
            # Try to extract JSON from the result
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{[^}]*\}', result, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    # Validate JSON
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    pass
            
            # Fallback: Create a basic evaluation
            fallback_evaluation = {
                "relevance_score": 3,
                "accuracy_score": 3,
                "completeness_score": 3,
                "overall_score": 3,
                "detailed_feedback": "Automated evaluation completed",
                "strengths": ["Response provided"],
                "areas_for_improvement": ["Could be more detailed"]
            }
            
            return json.dumps(fallback_evaluation)
            
        except Exception as e:
            logger.error(f"Error in answer evaluation: {e}")
            # Return error evaluation
            error_evaluation = {
                "relevance_score": 1,
                "accuracy_score": 1,
                "completeness_score": 1,
                "overall_score": 1,
                "detailed_feedback": f"Evaluation failed: {str(e)}",
                "strengths": [],
                "areas_for_improvement": ["Fix evaluation system"]
            }
            import json
            return json.dumps(error_evaluation)
    
    async def _arun(self, query: str, response: str, context: str = "") -> str:
        """Async version of the evaluator."""
        return self._run(query, response, context)


# Create a singleton instance
answer_evaluator_tool = AnswerEvaluatorTool()
