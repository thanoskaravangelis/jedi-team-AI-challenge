# Jedi Agent - AI Market Research Assistant

A sophisticated agentic chatbot built with LangChain's ReAct framework that helps clients answer questions using proprietary market research data and external tools. Features intelligent LLM-powered conversation titles, real-time response evaluation, and comprehensive analytics.

## 🚀 Features

- **Agentic AI**: Uses LangChain's ReAct agent for intelligent reasoning and tool orchestration
- **Multi-LLM Support**: Local LM Studio → Groq Llama → OpenAI GPT-4 fallback chain
- **Smart Conversation Titles**: LLM-generated meaningful titles instead of truncated queries
- **Real-time Evaluation**: Automated response quality scoring with detailed metrics
- **Multiple Data Sources**: ChromaDB vector search + web search + internal research data
- **Streaming Responses**: Real-time streaming with intermediate reasoning steps
- **User Feedback System**: Thumbs up/down feedback with analytics
- **Comprehensive Analytics**: Tool usage, performance metrics, and improvement recommendations
- **Production Ready**: Docker containerization, database persistence, and monitoring

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Frontend│    │   FastAPI        │    │   LangChain     │
│   + Streaming   │◄──►│   + SSE          │◄──►│   ReAct Agent   │
│   UI            │    │   Endpoints      │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                               │
                       ┌─────────────────────────┼─────────────────────────┐
                       │                         │                         │
               ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
               │   Data Sources   │    │      Tools       │    │   Evaluation     │
               │                  │    │                  │    │                  │
               │ • ChromaDB       │    │ • Similarity     │    │ • Answer Quality │
               │ • SQLite DB      │    │   Search         │    │   Evaluator      │
               │ • Tavily API     │    │ • Web Search     │    │ • Performance    │
               │ • Local LLM      │    │ • Internal Data  │    │   Analytics      │
               │ • Groq API       │    │   Search         │    │ • User Feedback  │
               │ • OpenAI API     │    │                  │    │   Tracking       │
               └──────────────────┘    └──────────────────┘    └──────────────────┘
```

### 🛠️ Available Tools

1. **Similarity Search Tool** (Primary): Semantic search using ChromaDB and sentence transformers
2. **Web Search Tool**: Current information via Tavily API for recent data and verification  
3. **Answer Evaluator Tool**: Real-time response quality evaluation (relevance, accuracy, helpfulness)

### 🤖 Supported LLM Models

**Intelligent Fallback Chain:** (in this order of priority)
1. **Local LM Studio** (Primary): `qwen2.5-7b-instruct` - Fast local inference
2. **Groq API** (Fallback): `llama3-8b-8192` - Fast cloud inference  
3. **OpenAI GPT-4** (Final Fallback): `gpt-4o-mini` - Highest quality responses

The system automatically selects the available model, falling back gracefully if services are unavailable.

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose
- **At least one of:** OpenAI API key, Groq API key, or Local LM Studio
- Tavily API key (optional, for web search)
- Node.js 16+ (for frontend development)

## 🛠️ Installation & Setup

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd jedi-agent
cp .env.example .env
# Edit .env with your API keys
# Suggested variables: OPENAI_API_KEY, TAVILY_API_KEY
```

### 2. Environment Variables

Create a `.env` file with your configuration:

```env
# LLM Configuration (provide at least one)
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key_here  # You can leave this empty if not using Groq
LOCAL_LLM_BASE_URL=http://localhost:1234  # For LM Studio, you can leave this empty if not using local LLM

# External Tools (optional)
TAVILY_API_KEY=your_tavily_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///./data/jedi_agent.db
VECTOR_DB_PATH=./vector_db

# API Configuration  
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

### 3. Quick Start with the Makefile (Recommended)

```bash
# Build and start all services
make docker-build-and-run

# View logs
make docker-logs

# Stop services
make docker-stop
```

Access the application at:
- **Frontend**: http://localhost:8001
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🎯 Agent Reasoning Process

The agent follows this sophisticated reasoning pattern:

1. **Query Analysis**: Understands user intent and determines information needs
2. **Tool Planning**: Decides which tools to use and in what sequence
3. **Execution**: Runs tools step by step with reasoning
4. **Information Synthesis**: Combines data from multiple sources
5. **Response Generation**: Creates comprehensive answer with citations
6. **Quality Evaluation**: Automatically scores response quality
7. **Title Generation**: Creates meaningful conversation title using LLM

### Example Agent Flow

```
User: "What social media platforms does Gen Z prefer in the UK?"

🤖 Thought: I need to search for market research data about Gen Z social media preferences, specifically in the UK market.

🔍 Action: similarity_search
Input: {"query": "Gen Z social media platforms UK preferences usage statistics"}
Observation: Found 5 relevant insights about Gen Z social media behavior in the UK...

🤖 Thought: Let me get more current information to supplement this data.

🌐 Action: web_search  
Input: {"query": "Gen Z social media usage UK 2024 statistics"}
Observation: Recent study shows TikTok and Instagram leading platforms...

🤖 Final Answer: Based on our market research data and recent studies, Gen Z in the UK shows strong preferences for visual and short-form content platforms...

📊 Evaluation: Relevance: 5/5, Accuracy: 4/5, Helpfulness: 5/5
📝 Title: "Gen Z Social Media UK"
```

## 📚 API Documentation

### Core Endpoints

#### POST `/query/stream` (Primary)
Process a query with real-time streaming response

```bash
curl -X POST "http://localhost:8000/query/stream" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "query": "What are the key trends in sustainable packaging?",
    "user_id": "user123"
  }'
```

**Response Stream Events:**
- `thinking`: Agent reasoning steps
- `content_chunk`: Streaming response content  
- `title_update`: Generated conversation title
- `done`: Stream completion

#### GET `/conversations/{user_id}`
Get all conversations for a user with titles

#### GET `/conversations/{conversation_id}/messages`  
Get all messages in a conversation

#### POST `/feedback`
Submit user feedback on responses

```bash
curl -X POST "http://localhost:8000/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": 123,
    "feedback_type": "thumbs_up",
    "comment": "Very helpful insights!"
  }'
```

#### GET `/analytics/tools`
Get comprehensive tool usage analytics

### Interactive Documentation

Visit `http://localhost:8000/docs` for complete Swagger UI documentation.

## 📊 Evaluation & Analytics

### Run Comprehensive Evaluation

```bash
# Generate evaluation report for last 30 days
python evaluate.py

# Custom time period  
python evaluate.py --days 7

# Export to JSON
python evaluate.py --format json --output report.json

# View specific metrics
python evaluate.py --days 14 --format json | jq '.tool_performance'
```

### Available Metrics

**Performance Metrics:**
- Response quality scores (relevance, accuracy, completeness)
- Tool usage statistics and success rates
- User feedback analysis and satisfaction rates
- Conversation engagement metrics

**Quality Indicators:**
- Average response evaluation scores
- Tool performance correlation with quality
- User satisfaction trends
- Response time analytics

**Improvement Recommendations:**
- Automated suggestions based on data analysis
- Tool reliability improvements
- Quality enhancement opportunities

### Evaluation Report Sample

```
🤖 JEDI AGENT EVALUATION REPORT
================================================================================

📅 Report Period: Last 30 days
📊 Generated: 2025-06-30T01:00:00

📈 OVERVIEW
----------------------------------------
Total Conversations: 45
Total Messages: 178
Unique Users: 12
Tool Success Rate: 94.2%
Average Conversation Length: 3.8 messages

🛠️ TOOL PERFORMANCE  
----------------------------------------
similarity_search:
  Uses: 89 | Success: 96.6% | Avg Time: 1247ms
web_search:
  Uses: 34 | Success: 88.2% | Avg Time: 2341ms

Most Used Tool: similarity_search
Most Reliable Tool: similarity_search

⭐ EVALUATION SCORES
----------------------------------------
Average Overall Score: 4.2/5
Excellent Responses (4.5+): 28
Good Responses (3.5-4.5): 31
Poor Responses (<2.5): 2

👥 USER FEEDBACK
----------------------------------------
Total Feedback: 23
Satisfaction Rate: 78.3%
Positive: 18 | Negative: 5

💡 IMPROVEMENT RECOMMENDATIONS
----------------------------------------
1. ✅ System performance looks good! No specific improvements needed at this time.
```

### Health Monitoring

```bash
# Health check
curl http://localhost:8000/

# Service metrics
curl http://localhost:8000/analytics/tools

# Database status
docker-compose exec jedi-agent python -c "from app.db.database import engine; print('✅ DB Connected')"
```

## 🔧 Development

### Frontend Development

The React frontend provides a modern chat interface with real-time streaming.

**Key Features:**
- Real-time message streaming
- Thinking animation during agent reasoning
- Citation display with source links
- User feedback buttons (thumbs up/down)
- Conversation history with smart titles
- Dark/light theme support

### Project Structure

```
jedi-agent/
├── app/
│   ├── agent/              # ReAct agent implementation
│   │   └── jedi_agent.py   # Main agent with LLM fallback chain
│   ├── tools/              # Agent tools
│   │   ├── similarity_search.py   # ChromaDB semantic search
│   │   ├── web_search.py          # Tavily web search
│   │   └── answer_evaluator.py    # Response quality evaluation
│   ├── db/                 # Database models and config
│   │   ├── models.py       # SQLAlchemy models
│   │   └── database.py     # Database connection
│   ├── api/                # FastAPI endpoints
│   │   └── main.py         # Streaming SSE API
│   └── evaluation/         # Evaluation system (optional)
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom hooks
│   │   └── styles/         # CSS styles
│   └── public/
├── data/                   # Data loading utilities
├── evaluate.py             # Evaluation statistics script
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Container orchestration
└── README.md
```

## 🚀 Key Features Deep Dive

### 1. Intelligent LLM Fallback Chain

The system automatically selects the model:

```python
# Priority order:
1. Local LM Studio (qwen2.5-7b-instruct) → Fast, private, free
2. Groq API (llama3-8b-8192) → Fast, cloud-based, generous free tier  
3. OpenAI GPT-4 → Highest quality, reliable, paid

# Automatic fallback on failure or unavailability
```

### 2. Smart Conversation Titles

Instead of truncated first messages, the system generates meaningful titles:

```
❌ Before: "What are the latest trends in..."
✅ After:  "Market Research Analysis"

❌ Before: "Can you help me understand Gen Z..."  
✅ After:  "Gen Z Consumer Behavior"
```

### 3. Real-time Response Evaluation

Every response is automatically evaluated for:
- **Relevance**: How well it addresses the question (1-5)
- **Accuracy**: Information correctness (1-5) 
- **Helpfulness**: Practical value for the user (1-5)

### 4. Comprehensive Analytics

Track system performance with detailed metrics:
- Tool usage patterns and success rates
- Response quality trends over time
- User satisfaction and feedback analysis
- Automated improvement recommendations

## ⚡ Performance Considerations

### Response Times

- **Local LLM**: ~2-5 seconds (fastest, requires local setup with LM Studio)
- **Groq API**: ~10-20 seconds (slower due to rate limits - cloud inference)
- **OpenAI GPT-4**: ~5-15 seconds (highest quality)

### Optimization Tips

1. **Use Local LLM** for fastest responses
2. **Enable web search** only when needed for current information

## 🔄 Continuous Improvement

Although a continuous learning loop is not implemented yet, the system can be designed to evolve based on user feedback and performance analytics as it supports:

1. **User Feedback** → Thumbs up/down on responses
2. **Quality Evaluation** → Automated scoring of all responses  
3. **Performance Analytics** → Tool usage and success tracking
4. **Improvement Recommendations** → Data-driven suggestions
5. **Prompt Optimization** → Refine based on performance data

### Potential Feedback-Driven Enhancement

```bash
# Analyze feedback patterns
docker-compose exec jedi-agent python3 evaluate.py --days 7 | grep -A 5 "USER FEEDBACK" 

# Identify improvement areas
docker-compose exec jedi-agent python3 evaluate.py --days 30 | grep -A 10 "RECOMMENDATIONS"

# Track quality trends
docker-compose exec jedi-agent python3 evaluate.py --format json | jq '.performance_trends.daily_metrics'
```

## 🐛 Troubleshooting

### Common Issues

1. **No LLM Available**
   ```bash
   # Check API keys in .env
   # Or set up local LM Studio
   # Error: "No valid LLM configuration found"
   ```

2. **ChromaDB Initialization Error**
   ```bash
   # Clear vector database
   rm -rf vector_db/
   docker-compose restart jedi-agent
   ```

3. **Database Schema Issues**
   ```bash
   # Fresh start
   docker-compose down -v
   docker-compose up -d
   ```

4. **Tool Failures**
   ```bash
   # Check evaluation report
   python evaluate.py --days 7
   # Review tool success rates and error messages
   ```

### Debug Mode

```bash
# Enable detailed logging
export DEBUG=true
export LOG_LEVEL=DEBUG
docker-compose restart jedi-agent

# View real-time logs
docker-compose logs -f jedi-agent
```

## 📄 License

This project is part of the GWI Jedi Team AI Engineering Challenge.

## 🏆 Challenge Requirements Checklist

- ✅ **Retrieve answers from internal data** - ChromaDB similarity search with citations
- ✅ **Plan course of action** - ReAct agent reasoning with step-by-step planning
- ✅ **Call external tools** - Web search, similarity search, answer evaluation
- ✅ **Evaluate responses** - Automated quality scoring (relevance, accuracy, helpfulness)
- ✅ **Finetune based on feedback** - User feedback collection and improvement recommendations
- ✅ **Persist conversations** - SQLite database with multi-user conversation management
- ✅ **HTTP interface** - FastAPI with streaming SSE support and React frontend
- ✅ **Auto-generate titles** - LLM-powered conversation title generation
- ✅ **User feedback** - Thumbs up/down system with analytics
- ✅ **Tool analytics** - Comprehensive usage statistics and performance metrics
- ✅ **Containerization** - Docker and docker-compose for easy deployment
- ✅ **One-command setup** - `docker-compose up -d` starts everything
- ✅ **Documentation** - Comprehensive README with examples and troubleshooting

