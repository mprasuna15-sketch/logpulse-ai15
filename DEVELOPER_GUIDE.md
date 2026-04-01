# LogPulse Project Documentation & Developer Guide

## 1. Project Overview
LogPulse is a high-performance system monitoring and log observability dashboard. It provides real-time streaming, anomaly detection, automated trace analysis, and AI-powered log summarization. The primary goal is to empower Site Reliability Engineers (SREs) with actionable insights derived from raw logs.

## 2. System Architecture
The application follows a modern decoupled architecture:
- **Frontend Panel**: A Next.js web application functioning as the user interface, visualizing metrics, trace flows, and live log streams.
- **Backend Service**: A FastAPI-based Python middleware that handles business logic, real-time WebSocket communication, log processing, and AI orchestration.
- **Data Source**: AWS CloudWatch serves as the primary ingress point for live system logs.
- **Vector Storage**: A local ChromaDB instance persists summarized logs and vectorized embeddings for historical semantic context.

## 3. Technology Stack & Tools

### Frontend
- **Framework**: Next.js (App Router) with React 19
- **Styling**: Tailwind CSS, `clsx`, `tailwind-merge`
- **Visualization**: Recharts for metrics and data trends
- **Animations**: Framer Motion for smooth UI transitions
- **Icons**: Lucide React
- **Performance Handling**: `react-window` for virtualizing large log lists

### Backend
- **Framework**: FastAPI (Python) for REST endpoints and WebSockets
- **Server**: Uvicorn as the ASGI server
- **Cloud/AWS SDK**: `boto3` for connecting to CloudWatch and Bedrock
- **Vector Database**: ChromaDB (Persistent storage)
- **Data processing**: Numpy for statistical data transformation, Python standard libraries for queuing (`deque`) and multithreading (`ThreadPoolExecutor`).

## 4. AI & LLM Integration
The intelligent backbone of LogPulse relies heavily on Large Language Models for unstructured data comprehension.
- **Provider**: AWS Bedrock
- **Agent LLM Model**: `us.meta.llama4-maverick-17b-instruct-v1:0`
  - *Purpose*: Operates as an "Expert SRE Agent". It ingests the semantic context, user query, statistical anomaly payloads, and chronological raw logs. It outputs a structured JSON response containing a root cause analysis and recommendations based on identified patterns.
- **Embedding Model**: `amazon.titan-embed-text-v1`
  - *Purpose*: Used for converting parsed logs (including log level, message, user ID, and correlation ID) into high-dimensional vector representations.

## 5. RAG (Retrieval-Augmented Generation) Architecture
LogPulse utilizes an advanced form of RAG to ensure "No Error Left Behind" when answering queries:

1. **Ingestion & Vectorization**: 
   - Logs arriving from AWS CloudWatch are continuously parsed and standardized. 
   - Each log is summarized and embedded via the Titan embedding model and immediately indexed in the persistent ChromaDB local storage.
2. **Context Retrieval**:
   - When a user asks a query, the backend filters available recent logs within the specified time period.
   - The user query is embedded and sent to ChromaDB to retrieve the most semantically similar historical logs (Top N results).
   - Simultaneously, exact keyword and Trace ID extractions are performed to capture precise needle-in-a-haystack metrics.
3. **Augmentation and Prompt Definition**:
   - The final prompt is constructed using:
     - Broad context: Total logs scanned and unique error patterns.
     - Statistical Anomalies (from the local `AnomalyDetector`).
     - Deep historical context from the Vector Database (The Semantic Matches).
     - Contextual timeline references (Recent direct logs).
4. **Generation**:
   - The Llama model receives the highly structured prompt and processes it, enforcing strict rules to prioritize specific tracing instructions, thereby overcoming hallucination issues often found in non-augmented generation. 

## 6. Live Telemetry & Streaming
- **WebSocket Feed**: The backend maintains a rolling internal cache (`deque` of size 100K) of the live system state. Any new ingestion immediately broadcasts to connected frontend clients via WebSockets.
- **Gap-Filling Mechanism**: To maintain data integrity against connection drops or sparse intervals, LogPulse possesses an auto-healing gap mechanism that retrospectively queries CloudWatch when an incomplete timeline is detected.
