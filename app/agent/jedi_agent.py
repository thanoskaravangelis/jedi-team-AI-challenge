"""Main agent implementation using LangChain's ReAct framework."""

import os
from typing import List, Dict, Any, Optional
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from app.tools.internal_search import InternalDataSearchTool
from app.tools.web_search import WebSearchTool
from app.tools.similarity_search import SimilaritySearchTool
from app.llm.groq_llm import create_groq_llm
from app.llm.local_llm import create_local_llm
import logging

logger = logging.getLogger(__name__)


class JediAgent:
    """Main agent class that orchestrates tools and reasoning."""
    
    def __init__(self):
        self.llm = None
        self.agent = None
        self.agent_executor = None
        self.tools = []
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the LLM and agent with tools."""
        try:
            # Try Local LM Studio first (fastest and most reliable for local setup)
            local_llm_url = os.getenv("LOCAL_LLM_BASE_URL")
            groq_api_key = os.getenv("GROQ_API_KEY")
            openai_api_key = os.getenv("OPENAI_API_KEY")
            
            if local_llm_url:
                logger.info("🏠 Initializing Local LM Studio LLM (Qwen2.5-7b-instruct)")
                try:
                    self.llm = create_local_llm(
                        base_url=local_llm_url,
                        model_name="qwen2.5-7b-instruct",
                        temperature=0.1,
                        max_tokens=1500
                    )
                    logger.info("✅ Local LM Studio LLM initialized successfully")
                except Exception as e:
                    logger.error(f"❌ Local LM Studio failed: {e}")
                    logger.info("🔄 Falling back to Groq...")
                    if groq_api_key and groq_api_key != "YOUR_GROQ_API_KEY_HERE":
                        self.llm = create_groq_llm(
                            api_key=groq_api_key,
                            model="llama3-8b-8192",
                            temperature=0.1,
                            max_tokens=1500
                        )
                        logger.info("✅ Groq LLM initialized as fallback")
                    else:
                        raise ValueError("Local LLM failed and no Groq API key available")
            elif groq_api_key and groq_api_key != "YOUR_GROQ_API_KEY_HERE":
                logger.info("🦙 Initializing Groq LLM (Fast and Free Llama) - Fallback")
                self.llm = create_groq_llm(
                    api_key=groq_api_key,
                    model="llama3-8b-8192",  # Fastest model
                    temperature=0.1,
                    max_tokens=1500  # Reduced for faster response
                )
                logger.info("✅ Groq LLM initialized successfully")
            elif openai_api_key:
                logger.info("🤖 Initializing OpenAI LLM (Final Fallback)")
                self.llm = ChatOpenAI(
                    api_key=openai_api_key,
                    model="gpt-4o-mini",
                    temperature=0.1,
                    max_tokens=4000
                )
                logger.info("✅ OpenAI LLM initialized successfully")
            else:
                raise ValueError("No LLM configured. Please set LOCAL_LLM_BASE_URL, GROQ_API_KEY, or OPENAI_API_KEY")

            
            # Initialize tools (always include all tools, even if they're not functional)
            self.tools = []
            
            # Core tools (should always work)
            # NOTE: Internal data search tool commented out - using similarity_search instead
            # try:
            #     internal_tool = InternalDataSearchTool()
            #     self.tools.append(internal_tool)
            #     logger.info("✅ InternalDataSearchTool initialized successfully")
            # except Exception as e:
            #     logger.error(f"❌ Failed to initialize InternalDataSearchTool: {e}")
            #     raise  # This one is critical
            
            # Optional tools (may fail due to missing dependencies or API keys)
            similarity_tool = SimilaritySearchTool()
            self.tools.append(similarity_tool)
            if hasattr(similarity_tool, 'chroma_client') and similarity_tool.chroma_client:
                logger.info("✅ SimilaritySearchTool initialized successfully (primary internal research)")
            else:
                logger.warning("⚠️ SimilaritySearchTool added but not functional (missing dependencies)")
            
            web_tool = WebSearchTool()
            self.tools.append(web_tool)
            if hasattr(web_tool, 'tavily_client') and web_tool.tavily_client:
                logger.info("✅ WebSearchTool initialized successfully")
            else:
                logger.warning("⚠️ WebSearchTool added but not functional (missing API key)")
            
            logger.info(f"🔧 Agent configured with {len(self.tools)} tools: {[tool.name for tool in self.tools]}")
            
            # Create the ReAct prompt template
            react_prompt = PromptTemplate.from_template("""
You are a specialized market research AI agent for GWI (Global Web Index). Your primary expertise is in analyzing and providing insights from market research data.

You have access to the following tools:
{tools}

Your goal is to provide helpful responses, using tools only when they add value to answer market research, consumer behavior, demographics, and related business questions.

CRITICAL: TOOL USAGE DECISION FRAMEWORK:

**WHEN TO USE TOOLS:**
- Market research questions (trends, consumer behavior, demographics)
- Business analysis requests (market size, competitive analysis)
- Data-driven insights needed (statistics, percentages, research findings)
- Industry-specific information requests
- Questions requiring current/recent information validation

**WHEN NOT TO USE TOOLS (respond directly):**
- Simple greetings ("hi", "hello", "good morning")
- Basic conversational responses ("thanks", "ok", "bye")
- General knowledge questions (capitals, basic math, definitions)
- Personal questions about yourself or capabilities
- Simple clarification requests
- Test messages or very short queries

DECISION PROCESS:
1. **First, assess the query type**: Is this a conversational message or a research question?
2. **If conversational/simple**: Respond directly without tools
3. **If research-related**: Then use appropriate tools

TOOL USAGE GUIDELINES (only for research queries):
- **Always start with similarity_search**: Check our proprietary market research database first
- **Then use web_search**: For current trends and external validation, even if internal results are found
- **Be thorough**: Use both tools for all research questions
- **Cite sources**: Always reference where information comes from

RESPONSE QUALITY EXPECTATIONS:
- For simple queries: Be friendly, concise, and conversational
- For research queries: Include specific data points, actionable insights, and proper citations
- Structure complex responses with clear sections and bullet points

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do and whether tools are needed
Action: the action to take, should be one of [{tool_names}] OR respond directly if no tools needed
Action Input: the input to the action (if using a tool)
Observation: the result of the action (if using a tool)
... (this Thought/Action/Action Input/Observation can repeat N times, but only for research questions)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

**EXAMPLES:**

Query: "Hi"
Thought: This is a simple greeting. No tools needed.
Final Answer: Hello! How can I assist you with market research insights today?

Query: "What are Gen Z social media trends?"
Thought: This is a market research question requiring tools and data.
Action: similarity_search
Action Input: Gen Z social media trends
Observation: [internal results]
Thought: I should also check current web sources for the latest trends.
Action: web_search
Action Input: Gen Z social media trends
Observation: [web results]
Thought: I now know the final answer
Final Answer: [combined answer from both sources]

Begin!

Previous conversation history:
{chat_history}

Question: {input}
Thought: {agent_scratchpad}
""")
            
            # Create the ReAct agent            
            # Create the ReAct agent
            self.agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=react_prompt
            )
            
            # Create agent executor with memory
            memory = ConversationBufferWindowMemory(
                memory_key="chat_history",
                return_messages=True,
                k=10  # Keep last 10 exchanges
            )
            
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                memory=memory,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=6,  # Reduced from 10 for faster execution
                early_stopping_method="force",  # Changed from "generate" to "force"
                return_intermediate_steps=True  # This is crucial for getting tool results!
            )
            
            logger.info("Jedi Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Jedi Agent: {e}")
            raise
    
    def process_query(self, query: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a user query and return the agent's response."""
        if not self.agent_executor:
            return {
                "error": "Agent not properly initialized",
                "response": "I'm sorry, but I'm not properly configured. Please check the system setup."
            }
        
        try:
            logger.info(f"Processing query: {query[:100]}...")
            
            # Load conversation history if continuing existing conversation
            if conversation_id and conversation_id != "None":
                self._load_conversation_history(conversation_id)
            
            # Execute the agent
            result = self.agent_executor.invoke({"input": query})
            
            response = {
                "query": query,
                "response": result.get("output", "No response generated"),
                "intermediate_steps": result.get("intermediate_steps", []),
                "conversation_id": conversation_id
            }
            
            logger.info(f"Query processed successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "error": str(e),
                "response": f"I encountered an error while processing your question: {str(e)}",
                "query": query,
                "conversation_id": conversation_id
            }
    
    def _load_conversation_history(self, conversation_id: str):
        """Load conversation history into agent memory."""
        try:
            from app.db.database import get_db
            from app.db.models import Message
            from sqlalchemy.orm import Session
            
            # Get database session
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                # Load messages from database
                messages = db.query(Message).filter(
                    Message.conversation_id == int(conversation_id)
                ).order_by(Message.created_at.asc()).all()
                
                logger.info(f"Loading {len(messages)} messages for conversation {conversation_id}")
                
                # Clear existing memory
                self.agent_executor.memory.clear()
                
                # Add messages to memory
                for message in messages[:-1]:  # Exclude the last message (current query)
                    if message.role == "user":
                        self.agent_executor.memory.chat_memory.add_user_message(message.content)
                    elif message.role == "assistant":
                        self.agent_executor.memory.chat_memory.add_ai_message(message.content)
                
                logger.info(f"✅ Loaded conversation history: {len(messages)} messages")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.warning(f"Could not load conversation history: {e}")
            # Continue without history if loading fails
    
    async def aprocess_query(self, query: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Async version of process_query."""
        # For now, we'll use the sync version as LangChain's async support is still evolving
        return self.process_query(query, conversation_id)
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return [tool.name for tool in self.tools]
    
    def reset_memory(self):
        """Reset the agent's conversation memory."""
        if self.agent_executor and hasattr(self.agent_executor, 'memory'):
            self.agent_executor.memory.clear()
            logger.info("Agent memory reset")


# Global agent instance
_agent_instance = None


def get_agent() -> JediAgent:
    """Get or create the global agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = JediAgent()
    return _agent_instance
