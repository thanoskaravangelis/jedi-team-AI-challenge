"""FastAPI application with SSE support for the Jedi Agent."""

import os
import json
import asyncio
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.database import get_db, init_db
from app.db.models import User, Conversation, Message, ToolInvocation, UserFeedback, EvaluationScore
from app.agent.jedi_agent import get_agent
from app.tools.answer_evaluator import answer_evaluator_tool
import logging
import time
import json

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Jedi Agent API",
    description="AI-powered market research assistant",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the web UI
app.mount("/ui", StaticFiles(directory="ui"), name="ui")


# Pydantic models for API
class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = "default_user"
    conversation_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    message_id: int
    feedback_type: str  # 'thumbs_up' or 'thumbs_down'
    comment: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


# Helper functions
def get_or_create_user(db: Session, username: str) -> User:
    """Get existing user or create new one."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_or_create_conversation(db: Session, user_id: int, conversation_id: Optional[str] = None) -> Conversation:
    """Get existing conversation or create new one."""
    if conversation_id and conversation_id != "None":
        # Handle both string and integer conversation IDs
        try:
            # Skip temp conversation IDs
            if str(conversation_id).startswith("temp-"):
                logger.info(f"Skipping temp conversation ID: {conversation_id}")
            else:
                conv_id = int(conversation_id)
                conversation = db.query(Conversation).filter(
                    Conversation.id == conv_id,
                    Conversation.user_id == user_id
                ).first()
                if conversation:
                    logger.info(f"Found existing conversation: {conv_id}")
                    return conversation
                else:
                    logger.warning(f"Conversation {conv_id} not found for user {user_id}")
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid conversation_id format: {conversation_id}, error: {e}")
    
    # Create new conversation
    conversation = Conversation(user_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    logger.info(f"Created new conversation: {conversation.id}")
    return conversation


def generate_initial_thinking(query: str, is_simple_query: bool) -> str:
    """Generate initial thinking content by getting the model's actual thought process for the query."""
    if is_simple_query:
        return f"I see you're asking: \"{query}\"\n\nLet me provide a helpful response to your question."
    
    # For complex queries, get the actual model's thinking process
    from app.agent.jedi_agent import get_agent
    agent = get_agent()
    
    thinking_prompt = f"""You are a market research AI. A user has asked: "{query}"

Before starting your research, briefly explain your initial thinking process about this query. Consider:
- What type of research question this is
- What approach you would take
- What you're looking for

Keep it concise (2-3 sentences) and natural. This is your initial thought process, not a formal analysis."""

    try:
        thinking_result = agent.llm.invoke(thinking_prompt)
        if hasattr(thinking_result, 'content'):
            return thinking_result.content.strip()
        return str(thinking_result).strip()
    except Exception as e:
        logger.warning(f"Failed to generate initial thinking: {e}")
        return f"Let me analyze your query: \"{query}\" and provide comprehensive market research insights."


def track_tool_invocation(db: Session, conversation_id: int, message_id: int, tool_name: str, 
                          input_data: str, output_data: str, success: bool, 
                          execution_time: int = None, error_message: str = None):
    """Track tool usage for analytics."""
    try:
        tool_invocation = ToolInvocation(
            conversation_id=conversation_id,
            message_id=message_id,
            tool_name=tool_name,
            input_data=input_data[:1000] if input_data else None,  # Limit length
            output_data=output_data[:2000] if output_data else None,  # Limit length
            success=success,
            execution_time=execution_time,
            error_message=error_message[:500] if error_message else None
        )
        db.add(tool_invocation)
        db.commit()
        logger.info(f"📊 Tracked tool invocation: {tool_name} (success: {success})")
    except Exception as e:
        logger.error(f"Error tracking tool invocation: {e}")


def evaluate_response_quality(db: Session, message_id: int, query: str, response: str, 
                             tools_used: list = None):
    """Evaluate response quality using the answer evaluator tool (backend only)."""
    try:
        context = f"Tools used: {', '.join(tools_used)}" if tools_used else "No tools used"
        
        # Run evaluation (this won't be yielded to frontend)
        evaluation_result = answer_evaluator_tool._run(query, response, context)
        
        # Parse evaluation results
        evaluation_data = json.loads(evaluation_result)
        
        # Save evaluation to database
        evaluation_score = EvaluationScore(
            message_id=message_id,
            relevance_score=evaluation_data.get('relevance_score'),
            accuracy_score=evaluation_data.get('accuracy_score'),
            completeness_score=evaluation_data.get('completeness_score'),
            overall_score=evaluation_data.get('overall_score'),
            evaluation_notes=evaluation_data.get('detailed_feedback', '')
        )
        
        db.add(evaluation_score)
        db.commit()
        
        logger.info(f"✅ Evaluated response quality for message {message_id}: "
                   f"Overall: {evaluation_data.get('overall_score', 'N/A')}/5")
        
    except Exception as e:
        logger.error(f"Error evaluating response quality: {e}")


def generate_conversation_title(first_message: str) -> str:
    """Generate a meaningful title for the conversation using LLM."""
    try:
        # Get the agent's LLM for title generation
        agent = get_agent()
        
        # Create a focused prompt for title generation
        title_prompt = f"""Generate a concise, descriptive title (3-6 words) for a conversation that starts with this user question:

"{first_message}"

Requirements:
- Maximum 6 words
- Capture the main topic/intent
- Professional and clear
- No quotes or special characters
- Examples: "Market Research Analysis", "Product Launch Strategy", "Customer Behavior Insights"

Title:"""

        # Generate title using the LLM
        response = agent.llm.invoke(title_prompt)
        
        # Extract and clean the title
        title = response.content.strip()
        
        # Remove quotes if present
        title = title.strip('"\'')
        
        # Limit to 6 words and ensure it's not too long
        words = title.split()[:6]
        title = " ".join(words)
        
        # Fallback to simple generation if title is too short or generic
        if len(title) < 3 or title.lower() in ['conversation', 'chat', 'question', 'query']:
            words = first_message.split()[:6]
            title = " ".join(words)
            if len(first_message.split()) > 6:
                title += "..."
            title = title.capitalize()
        
        logger.info(f"📝 Generated conversation title: '{title}' for query: '{first_message[:50]}...'")
        return title.capitalize()
        
    except Exception as e:
        logger.error(f"Error generating LLM title: {e}, falling back to simple generation")
        # Fallback to simple title generation
        words = first_message.split()[:6]
        title = " ".join(words)
        if len(first_message.split()) > 6:
            title += "..."
        return title.capitalize()


def extract_summary_and_clean_response(agent_response: str) -> (str, str):
    """Extract the Final Answer (summary) and remove the Sources section from the response."""
    summary = None
    cleaned = agent_response

    # Simple approach: everything after "Final Answer:" until sources
    if "Final Answer:" in agent_response:
        # Get everything after "Final Answer:"
        after_final = agent_response.split("Final Answer:", 1)[1].strip()
        
        # Remove sources section if it exists
        sources_patterns = ["### Sources:", "\nSources:", "\n- ["]
        for pattern in sources_patterns:
            if pattern in after_final:
                after_final = after_final.split(pattern, 1)[0]
        
        # Remove markdown links [text](url)
        import re
        after_final = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', after_final)
        
        summary = after_final.strip()
        logger.info(f"✅ Extracted final answer ({len(summary)} chars)")
    else:
        summary = agent_response.strip()
        # Remove markdown links from full response too
        import re
        summary = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', summary)
        logger.info("No Final Answer found, using full response.")

    # Clean the response by removing Final Answer section
    cleaned = re.sub(r"Final Answer:.*", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = cleaned.strip()
    
    return summary, cleaned


# API Routes
@app.on_event("startup")
async def startup_event():
    """Initialize database and agent on startup."""
    logger.info("Starting Jedi Agent API...")
    init_db()
    # Initialize agent (this will also populate ChromaDB if needed)
    get_agent()
    logger.info("Jedi Agent API started successfully")


@app.get("/")
async def root():
    """Redirect to the web UI."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Jedi Agent - Market Research Assistant</title>
        <meta http-equiv="refresh" content="0; url=/ui/">
    </head>
    <body>
        <p>Redirecting to <a href="/ui/">Jedi Agent Web UI</a>...</p>
    </body>
    </html>
    """)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"message": "Jedi Agent API is running", "status": "healthy"}


@app.post("/query")
async def query_agent(request: QueryRequest, db: Session = Depends(get_db)):
    """Process a query through the agent (non-streaming)."""
    try:
        # Get or create user and conversation
        user = get_or_create_user(db, request.user_id)
        conversation = get_or_create_conversation(db, user.id, request.conversation_id)
        
        # Save user message
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=request.query
        )
        db.add(user_message)
        
        # Generate conversation title if this is the first message
        if not conversation.title:
            conversation.title = generate_conversation_title(request.query)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        db.commit()
        
        # Process query with agent
        agent = get_agent()
        result = agent.process_query(request.query, str(conversation.id))

        # Extract summary and clean response
        summary, cleaned_response = extract_summary_and_clean_response(result.get("response", ""))

        # Save agent response
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=cleaned_response,
            message_metadata=json.dumps({
                "intermediate_steps": result.get("intermediate_steps", []),
                "tools_used": [step[0].tool for step in result.get("intermediate_steps", []) if hasattr(step[0], 'tool')],
                "summary": summary
            })
        )
        db.add(assistant_message)
        db.commit()

        return {
            "response": cleaned_response,
            "summary": summary,
            "conversation_id": conversation.id,
            "message_id": assistant_message.id,
            "intermediate_steps": result.get("intermediate_steps", [])
        }
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def parse_tool_citations(observation: str, tool_name: str) -> list:
    """Parse structured citations from tool response."""
    citations = []
    
    try:
        if "---CITATIONS_START---" in observation and "---CITATIONS_END---" in observation:
            # Extract citations section
            start_idx = observation.find("---CITATIONS_START---")
            end_idx = observation.find("---CITATIONS_END---")
            citations_section = observation[start_idx:end_idx]
            
            # Parse individual citations
            lines = citations_section.split('\n')
            for line in lines:
                if line.startswith("CITATION|"):
                    # Similarity search citation format: CITATION|rank|similarity|content
                    parts = line.split('|', 3)
                    if len(parts) >= 4:
                        rank, similarity, content = parts[1], parts[2], parts[3]
                        citations.append({
                            "type": "internal",
                            "source": "Internal Market Research Database",
                            "data": content,
                            "relevance": f"Primary research insight (Similarity: {similarity})",
                            "rank": int(rank),
                            "similarity": float(similarity)
                        })
                
                elif line.startswith("WEB_CITATION|"):
                    # Web search citation format: WEB_CITATION|rank|score|title|url|content
                    parts = line.split('|', 5)
                    if len(parts) >= 6:
                        rank, score, title, url, content = parts[1], parts[2], parts[3], parts[4], parts[5]
                        citations.append({
                            "type": "web",
                            "source": title,
                            "url": url,
                            "snippet": content[:200] + "..." if len(content) > 200 else content,
                            "relevance": f"External market research (Relevance: {score})",
                            "rank": int(rank),
                            "score": float(score)
                        })
            
            logger.info(f"📊 Parsed {len(citations)} structured citations from {tool_name}")
            
    except Exception as e:
        logger.warning(f"Failed to parse structured citations from {tool_name}: {e}")
        
    return citations


@app.post("/query/stream")
async def stream_query(request: QueryRequest, db: Session = Depends(get_db)):
    """Process a query through the agent with streaming response."""
    async def generate_stream():
        response_sent = False
        try:
            # Validate request
            if not request.query or not request.query.strip():
                yield f"data: {json.dumps({'type': 'error', 'message': 'Query cannot be empty'})}\n\n"
                return
            
            # Log request details for debugging
            logger.info(f"📨 Stream request: query='{request.query[:50]}...', user_id='{request.user_id}', conversation_id='{request.conversation_id}'")
            
            # Get or create user and conversation
            user = get_or_create_user(db, request.user_id)
            conversation = get_or_create_conversation(db, user.id, request.conversation_id)
            
            # Log conversation info for debugging
            logger.info(f"📝 Processing query for conversation {conversation.id} (requested: {request.conversation_id})")
            
            # Save user message
            user_message = Message(
                conversation_id=conversation.id,
                role="user",
                content=request.query
            )
            db.add(user_message)
            
            # Generate conversation title if this is the first message
            if not conversation.title:
                conversation.title = generate_conversation_title(request.query)
                yield f"data: {json.dumps({'type': 'title_update', 'title': conversation.title, 'conversation_id': conversation.id})}\n\n"
            
            conversation.updated_at = datetime.utcnow()
            db.commit()
            
            # Check if this is a simple conversational query that doesn't need tools
            simple_queries = [
                'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
                'how are you', 'what\'s up', 'thanks', 'thank you', 'bye', 'goodbye',
                'test', 'testing', 'ok', 'okay', 'yes', 'no', 'cool', 'nice'
            ]
            
            query_lower = request.query.lower().strip()
            is_simple_query = (
                len(request.query.split()) <= 2 and  # Very short queries only
                any(simple_word in query_lower for simple_word in simple_queries)
            ) or len(request.query.strip()) <= 3  # Very very short queries
            
            logger.info(f"🤔 Query classification: '{request.query}' -> simple={is_simple_query}")
            
            # Process query with agent
            agent = get_agent()
            
            # ALWAYS generate and yield initial thinking (even for shorter queries)
            initial_thinking = generate_initial_thinking(request.query, is_simple_query)
            logger.info(f"🧠 Generated initial thinking: {initial_thinking[:100]}...")
            yield f"data: {json.dumps({'type': 'initial_thinking', 'data': initial_thinking})}\n\n"
            logger.info("🧠 Yielded initial thinking to frontend")
            await asyncio.sleep(0.8)  # Give users time to read the initial thinking
            
            if is_simple_query:
                # For simple queries, send minimal thinking and get direct response
                yield f"data: {json.dumps({'type': 'thinking', 'data': 'Processing your message...', 'tool': 'system'})}\n\n"
                await asyncio.sleep(0.2)
            else:
                # For complex queries, send analysis thinking
                yield f"data: {json.dumps({'type': 'thinking', 'data': 'Starting research and analysis...', 'tool': 'system'})}\n\n"
                await asyncio.sleep(0.3)
                yield f"data: {json.dumps({'type': 'thinking', 'data': 'Identifying key areas to investigate...', 'tool': 'system'})}\n\n"
                await asyncio.sleep(0.2)
            
            result = agent.process_query(request.query, str(conversation.id))
            
            # Debug: Log what we got from agent
            logger.info(f"Agent result keys: {list(result.keys())}")
            intermediate_steps = result.get('intermediate_steps', [])
            logger.info(f"Intermediate steps count: {len(intermediate_steps)}")
            
            # Check if any tools were actually used
            tools_actually_used = len(intermediate_steps) > 0
            has_tool_results = False
            
            # Collect and organize citations by source type
            internal_citations = []
            web_citations = []
            other_citations = []
            tools_used = []
            
            # Process intermediate steps and extract citations in real-time
            for i, step in enumerate(intermediate_steps):
                # step[0] is the action, step[1] is the observation
                action = step[0]
                observation = step[1] if len(step) > 1 else ''
                
                tool_name = getattr(action, 'tool', 'unknown') if hasattr(action, 'tool') else 'unknown'
                tool_input = getattr(action, 'tool_input', {}) if hasattr(action, 'tool_input') else {}
                
                logger.info(f"Processing step {i}: tool={tool_name}, observation_length={len(observation)}")
                
                if tool_name not in tools_used:
                    tools_used.append(tool_name)
                
                # Track tool execution time (rough estimate)
                tool_start_time = time.time()
                
                # Determine if tool execution was successful
                tool_success = observation and len(observation.strip()) > 10
                error_message = None
                if not tool_success:
                    error_message = "No meaningful output generated"
                
                # Track tool invocation for analytics
                execution_time = int((time.time() - tool_start_time) * 1000)  # Convert to milliseconds
                # We'll track this after we have the message_id
                
                # Send thinking message with tool input details
                thinking_messages = {
                    'similarity_search': 'Searching internal market research database...',
                    'web_search': 'Analyzing current web sources and reports...',
                }
                
                thinking_msg = thinking_messages.get(tool_name, f'Using {tool_name}...')
                
                # Add query details to thinking message
                if isinstance(tool_input, dict) and 'query' in tool_input:
                    query_text = tool_input['query'][:50] + "..." if len(tool_input['query']) > 50 else tool_input['query']
                    thinking_msg += f" Query: '{query_text}'"
                
                yield f"data: {json.dumps({'type': 'thinking', 'data': thinking_msg, 'tool': tool_name})}\n\n"
                await asyncio.sleep(0.1)
                
                # Extract and categorize citation information immediately
                if observation and len(observation.strip()) > 10:
                    logger.info(f"Tool {tool_name} produced observation: {observation[:100]}...")
                    
                    # Check if tool found actual results (not just "no results found")
                    no_results_indicators = [
                        "No sufficiently similar insights found",
                        "No similar market research insights found",
                        "No meaningful web search results found",
                        "threshold:", "Try lowering",
                        "not available", "disabled"
                    ]
                    
                    has_actual_results = not any(indicator.lower() in observation.lower() for indicator in no_results_indicators)
                    
                    if has_actual_results:
                        has_tool_results = True  # Mark that we have meaningful tool results
                    
                    # Parse structured citations from tool responses
                    parsed_citations = parse_tool_citations(observation, tool_name)
                    
                    if tool_name == 'similarity_search' and has_actual_results:
                        # Extract similarity search citations only if there are actual results
                        if parsed_citations:
                            internal_citations.extend(parsed_citations)
                            logger.info(f"✅ Added {len(parsed_citations)} internal citations from similarity search")
                        elif "Citation" in observation and "Similarity:" in observation:
                            # Fallback citation if parsing fails but we have results
                            citation = {
                                "type": "internal",
                                "source": "Internal Market Research Database",
                                "data": observation[:500] + "..." if len(observation) > 500 else observation,
                                "relevance": "Primary demographic and behavioral insights from knowledge base"
                            }
                            internal_citations.append(citation)
                            logger.info(f"✅ Added fallback internal citation from similarity search")
                        
                    elif tool_name == 'web_search' and has_actual_results:
                        # Extract web search citations only if there are actual results
                        if parsed_citations:
                            web_citations.extend(parsed_citations)
                            logger.info(f"✅ Added {len(parsed_citations)} web citations from web search")
                        elif "Web Result" in observation or "AI Summary:" in observation:
                            # Fallback citation if parsing fails but we have results
                            citation = {
                                "type": "web", 
                                "source": "Current Market Research Reports",
                                "snippet": observation[:400] + "..." if len(observation) > 400 else observation,
                                "relevance": "Current market trend validation"
                            }
                            web_citations.append(citation)
                            logger.info(f"✅ Added fallback web citation from web search")
                    
                    # Send tool completion message with result summary
                    if has_actual_results:
                        if tool_name == 'similarity_search':
                            yield f"data: {json.dumps({'type': 'thinking', 'data': f'Found {len(parsed_citations)} relevant internal insights', 'tool': tool_name})}\n\n"
                        elif tool_name == 'web_search':
                            yield f"data: {json.dumps({'type': 'thinking', 'data': f'Retrieved {len(parsed_citations)} current market reports', 'tool': tool_name})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'thinking', 'data': f'No relevant results found in {tool_name}', 'tool': tool_name})}\n\n"
                        
                else:
                    logger.warning(f"Tool {tool_name} produced empty or short observation: '{observation[:50]}'")
                    yield f"data: {json.dumps({'type': 'thinking', 'data': f'Tool {tool_name} completed with no results', 'tool': tool_name})}\n\n"
            
            # Log total citations and determine response format
            total_citations = len(internal_citations + web_citations + other_citations)
            logger.info(f"📊 Total citations extracted: Internal={len(internal_citations)}, Web={len(web_citations)}, Other={len(other_citations)}, Total={total_citations}")
            
            # Get the main response from agent
            agent_response = result.get("response", "")

            # Extract summary and clean response for streaming
            summary, cleaned_response = extract_summary_and_clean_response(agent_response)

            # Determine if this should be a simple chat response or complex research response
            should_be_simple = (
                is_simple_query or  # Originally detected as simple
                not tools_actually_used or  # No tools were used
                not has_tool_results or  # Tools used but no meaningful results
                total_citations == 0  # No citations found
            )

            if should_be_simple:
                # Simple chat response - just the agent's answer, no complex formatting
                yield f"data: {json.dumps({'type': 'simple_response', 'data': cleaned_response, 'summary': summary})}\n\n"
                await asyncio.sleep(0.2)
                complete_response = cleaned_response
            else:
                # Complex research response with citations and sections
                yield f"data: {json.dumps({'type': 'thinking', 'data': 'Building structured response...', 'tool': 'system'})}\n\n"
                await asyncio.sleep(0.2)
                content_streamed = False
                
                # Stream the final answer FIRST as the main response
                if summary and summary.strip():
                    summary_content = f"**📝 Key Insights**\n\n{summary}"
                    yield f"data: {json.dumps({'type': 'content_chunk', 'section': 'summary', 'data': summary_content, 'citations': []})}\n\n"
                    await asyncio.sleep(0.4)
                    content_streamed = True
                
                # Then show supporting evidence from tools
                if internal_citations and len(internal_citations) > 0:
                    internal_section = f"""**📊 Supporting Research: Internal Database**\n\nBased on our proprietary market research database:\n\n{generate_internal_insights_from_citations(internal_citations)}"""
                    yield f"data: {json.dumps({'type': 'content_chunk', 'section': 'internal', 'data': internal_section, 'citations': internal_citations})}\n\n"
                    await asyncio.sleep(0.4)
                    content_streamed = True
                if web_citations and len(web_citations) > 0:
                    web_section = f"""**🌐 Supporting Research: Current Intelligence**\n\n{generate_web_insights_from_citations(web_citations)}"""
                    yield f"data: {json.dumps({'type': 'content_chunk', 'section': 'web', 'data': web_section, 'citations': web_citations})}\n\n"
                    await asyncio.sleep(0.4)
                    content_streamed = True
                # Stream the summary/Final Answer at the end if present
                # (already sent above)
                all_sections = []
                if internal_citations:
                    all_sections.append("Internal Market Research Insights")
                if web_citations:
                    all_sections.append("Web Search Insights")
                all_sections.append("Analysis Summary")
                complete_response = f"Analysis completed with {len(all_sections)} sections using {total_citations} data sources."
            # Save response to database
            # Include initial thinking in the final saved message for complex queries
            final_content = complete_response
            if not is_simple_query:
                initial_thinking = generate_initial_thinking(request.query, is_simple_query)
                final_content = initial_thinking + "\n\n" + complete_response
            
            metadata_dict = {
                "tools_used": tools_used,
                "is_simple_response": should_be_simple,
                "total_citations": total_citations,
                "summary": summary,
                "has_initial_thinking": not is_simple_query
            }
            if not should_be_simple:
                metadata_dict.update({
                    "internal_citations": internal_citations,
                    "web_citations": web_citations, 
                    "other_citations": other_citations,
                    "sections": all_sections if 'all_sections' in locals() else []
                })
            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=final_content,
                message_metadata=json.dumps(metadata_dict)
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)  # Get the generated ID
            
            # Track tool invocations for analytics
            for i, step in enumerate(intermediate_steps):
                action = step[0]
                observation = step[1] if len(step) > 1 else ''
                tool_name = getattr(action, 'tool', 'unknown') if hasattr(action, 'tool') else 'unknown'
                tool_input = getattr(action, 'tool_input', {}) if hasattr(action, 'tool_input') else {}
                
                # Determine success and timing
                tool_success = observation and len(observation.strip()) > 10
                error_message = "No meaningful output generated" if not tool_success else None
                execution_time = 1000  # Rough estimate in milliseconds
                
                # Track this tool invocation
                track_tool_invocation(
                    db=db,
                    conversation_id=conversation.id,
                    message_id=assistant_message.id,
                    tool_name=tool_name,
                    input_data=json.dumps(tool_input) if tool_input else None,
                    output_data=observation[:2000] if observation else None,
                    success=tool_success,
                    execution_time=execution_time,
                    error_message=error_message
                )
            
            # Evaluate response quality (backend only - not yielded to frontend)
            evaluate_response_quality(
                db=db,
                message_id=assistant_message.id,
                query=request.query,
                response=final_content,
                tools_used=tools_used
            )
            
            # Send final conversation ID and message ID to frontend
            yield f"data: {json.dumps({'type': 'conversation_update', 'conversation_id': conversation.id})}\n\n"
            yield f"data: {json.dumps({'type': 'message_id_update', 'message_id': assistant_message.id})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in stream_query: {str(e)}", exc_info=True)
            if not response_sent:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    def _parse_tool_citations(self, observation: str, tool_name: str) -> list:
        """Parse structured citations from tool response."""
        citations = []
        
        try:
            if "---CITATIONS_START---" in observation and "---CITATIONS_END---" in observation:
                # Extract citations section
                start_idx = observation.find("---CITATIONS_START---")
                end_idx = observation.find("---CITATIONS_END---")
                citations_section = observation[start_idx:end_idx]
                
                # Parse individual citations
                lines = citations_section.split('\n')
                for line in lines:
                    if line.startswith("CITATION|"):
                        # Similarity search citation format: CITATION|rank|similarity|content
                        parts = line.split('|', 3)
                        if len(parts) >= 4:
                            rank, similarity, content = parts[1], parts[2], parts[3]
                            citations.append({
                                "type": "internal",
                                "source": "Internal Market Research Database",
                                "data": content,
                                "relevance": f"Primary research insight (Similarity: {similarity})",
                                "rank": int(rank),
                                "similarity": float(similarity)
                            })
                    
                    elif line.startswith("WEB_CITATION|"):
                        # Web search citation format: WEB_CITATION|rank|score|title|url|content
                        parts = line.split('|', 5)
                        if len(parts) >= 6:
                            rank, score, title, url, content = parts[1], parts[2], parts[3], parts[4], parts[5]
                            citations.append({
                                "type": "web",
                                "source": title,
                                "url": url,
                                "snippet": content[:200] + "..." if len(content) > 200 else content,
                                "relevance": f"External market research (Relevance: {score})",
                                "rank": int(rank),
                                "score": float(score)
                            })
                
                logger.info(f"📊 Parsed {len(citations)} structured citations from {tool_name}")
                
        except Exception as e:
            logger.warning(f"Failed to parse structured citations from {tool_name}: {e}")
            
        return citations
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


def generate_internal_insights_from_citations(citations: list) -> str:
    """Generate a summary paragraph of the internal insights using the LLM model."""
    if not citations:
        return "No specific internal insights were found for this query in our proprietary market research database."
    from app.agent.jedi_agent import get_agent
    agent = get_agent()
    # Concatenate all insight texts
    insights = [citation.get('data', '') for citation in citations if citation.get('data')]
    if not insights:
        return "No specific internal insights were found for this query in our proprietary market research database."
    joined = "\n".join(insights)
    prompt = f"Summarize the following internal market research findings into a concise, readable paragraph for a business audience.\n\nFINDINGS:\n{joined}\n\nSUMMARY:"  # Prompt for the LLM
    summary_result = agent.llm.invoke(prompt)
    if hasattr(summary_result, 'content'):
        return summary_result.content.strip()
    return str(summary_result).strip()


def generate_web_insights_from_citations(citations: list) -> str:
    """Generate a summary paragraph of the web insights using the LLM model."""
    if not citations:
        return "No current web insights were found for this query."
    from app.agent.jedi_agent import get_agent
    agent = get_agent()
    # Concatenate all web snippets
    insights = [citation.get('snippet', citation.get('data', '')) for citation in citations if citation.get('snippet') or citation.get('data')]
    if not insights:
        return "No current web insights were found for this query."
    joined = "\n".join(insights)
    prompt = f"Summarize the following web-based market research findings into a concise, readable paragraph for a business audience.\n\nFINDINGS:\n{joined}\n\nSUMMARY:"  # Prompt for the LLM
    summary_result = agent.llm.invoke(prompt)
    if hasattr(summary_result, 'content'):
        return summary_result.content.strip()
    return str(summary_result).strip()


def generate_web_source_list(citations: list) -> str:
    """Generate a clean list of web sources."""
    sources = []
    for citation in citations[:3]:
        source = citation.get('source', 'Web Source')
        url = citation.get('url', '')
        if url:
            sources.append(f"[{source}]({url})")
        else:
            sources.append(source)
    
    return ", ".join(sources) if sources else "Web sources"


def generate_other_insights_from_citations(citations: list) -> str:
    """Generate insights from other citations."""
    insights = []
    for i, citation in enumerate(citations[:2], 1):  # Limit to top 2
        data = citation.get('data', '')
        if data:
            summary = data[:100] + "..." if len(data) > 100 else data
            insights.append(f"• **Related Study {i}**: {summary}")
    
    if not insights:
        insights = [
            "• **Cross-Reference Data**: Supporting research from knowledge base",
            "• **Historical Context**: Previous studies confirm ongoing trends"
        ]
    
    return "\n".join(insights)


@app.get("/conversations/{user_id}")
async def get_user_conversations(user_id: str, db: Session = Depends(get_db)) -> List[ConversationResponse]:
    """Get all conversations for a user."""
    user = db.query(User).filter(User.username == user_id).first()
    if not user:
        return []
    
    conversations = db.query(Conversation).filter(
        Conversation.user_id == user.id
    ).order_by(Conversation.updated_at.desc()).all()
    
    result = []
    for conv in conversations:
        message_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
        result.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=message_count
        ))
    
    return result


@app.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int, db: Session = Depends(get_db)) -> List[MessageResponse]:
    """Get all messages in a conversation."""
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    result = []
    for msg in messages:
        metadata = None
        if msg.message_metadata:
            try:
                metadata = json.loads(msg.message_metadata)
            except json.JSONDecodeError:
                pass
        
        # Get feedback for this message if it exists
        feedback = db.query(UserFeedback).filter(
            UserFeedback.message_id == msg.id
        ).first()
        
        # Add feedback info to metadata
        if metadata is None:
            metadata = {}
        
        if feedback:
            metadata['user_feedback'] = {
                'type': feedback.feedback_type,
                'comment': feedback.comment,
                'created_at': feedback.created_at.isoformat()
            }
        else:
            metadata['user_feedback'] = None
        
        result.append(MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
            metadata=metadata
        ))
    
    return result


@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """Submit user feedback on a message."""
    # Verify message exists
    message = db.query(Message).filter(Message.id == request.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check if feedback already exists for this message
    existing_feedback = db.query(UserFeedback).filter(
        UserFeedback.message_id == request.message_id
    ).first()
    
    if existing_feedback:
        # Update existing feedback
        existing_feedback.feedback_type = request.feedback_type
        existing_feedback.comment = request.comment
        existing_feedback.created_at = datetime.utcnow()  # Update timestamp
        db.commit()
        return {"message": "Feedback updated successfully", "action": "updated"}
    else:
        # Create new feedback
        feedback = UserFeedback(
            message_id=request.message_id,
            feedback_type=request.feedback_type,
            comment=request.comment
        )
        db.add(feedback)
        db.commit()
        return {"message": "Feedback submitted successfully", "action": "created"}


@app.get("/analytics/tools")
async def get_tool_analytics(db: Session = Depends(get_db)):
    """Get analytics on tool usage."""
    # This is a basic implementation - could be expanded significantly
    from sqlalchemy import func
    
    tool_usage = db.query(
        ToolInvocation.tool_name,
        func.count(ToolInvocation.id).label('usage_count'),
        func.avg(ToolInvocation.execution_time).label('avg_execution_time')
    ).group_by(ToolInvocation.tool_name).all()
    
    return {
        "tool_usage": [
            {
                "tool_name": usage.tool_name,
                "usage_count": usage.usage_count,
                "avg_execution_time": usage.avg_execution_time
            }
            for usage in tool_usage
        ]
    }


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Delete a conversation and all its messages."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Delete all messages in the conversation
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    
    # Delete the conversation
    db.delete(conversation)
    db.commit()
    
    return {"message": "Conversation deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )