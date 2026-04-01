from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import boto3
import json
import uuid
from datetime import datetime, timedelta
import asyncio
from collections import deque
import traceback
import concurrent.futures
import functools
import os
import logging
from anomaly_detector import AnomalyDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
from vector_store import VectorStore
from logParser import parseLogs, RawLogEntry, get_unique_patterns

app = FastAPI()
detector = AnomalyDetector()
vector_store = VectorStore(region_name="us-east-1")

# --- CORS setup ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuration ---
API_KEY = os.getenv("LOG_PULSE_API_KEY", "dev-secret-key")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def validate_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key

# --- AWS Clients ---
DEFAULT_REGION = os.getenv("AWS_REGION", "us-east-1")
LOG_REGION = os.getenv("LOG_REGION", "us-east-2")

bedrock_client = boto3.client(
    service_name="bedrock-runtime",
    region_name=DEFAULT_REGION
)

cloudwatch_client = boto3.client(
    service_name="logs",
    region_name=LOG_REGION
)

MODEL_ID = os.getenv("ANALYSIS_MODEL_ID", "us.meta.llama4-maverick-17b-instruct-v1:0")

LOG_GROUP_NAME = os.getenv("LOG_GROUP_NAME", "/ecs/she-careers-api-prod")
LOG_STREAM_PREFIX = os.getenv("LOG_STREAM_PREFIX", "")

# --- In-memory cache for live logs ---
live_log_cache = deque(maxlen=100000)
cache_lock = asyncio.Lock()

# --- Thread Pool for Blocking I/O ---
executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

async def run_in_thread(func, *args, **kwargs):
    """Helper to run synchronous functions in the thread pool"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, functools.partial(func, *args, **kwargs))

# --- API models ---
class AnalyzeRequest(BaseModel):
    input: str
    time_filter: str = "1h"
    custom_start: Optional[int] = None
    custom_end: Optional[int] = None
    history: Optional[List[Dict[str, Any]]] = None

class LogFinding(BaseModel):
    id: str
    what: str
    when: str
    why: str
    how: str
    recommendation: str

class AnalyzeResponse(BaseModel):
    summary: str
    findings: List[LogFinding]
    time_period: str
    logs_analyzed: int
    is_live: bool

class TimeFilterRequest(BaseModel):
    time_filter: str
    custom_start: Optional[int] = None
    custom_end: Optional[int] = None

class LogsResponse(BaseModel):
    logs: List[dict]
    time_period: str
    total_count: int
    is_live: bool

class TraceFlowRequest(BaseModel):
    correlation_id: str

class TraceStep(BaseModel):
    id: str
    timestamp: str
    message: str
    level: str
    duration_ms: Optional[int]
    is_error: bool
    category: str
    step_number: int

class TraceFlowResponse(BaseModel):
    correlation_id: str
    steps: List[TraceStep]
    total_duration_ms: int
    start_time: str
    end_time: str
    status: str
    error_steps: List[int]

class CloudWatchConfig(BaseModel):
    log_group_name: str
    log_stream_prefix: Optional[str] = ""

class LogStreamUpdate(BaseModel):
    log: dict
    total_logs: int
    timestamp: str

# --- Helper Functions ---

def get_time_range(time_filter: str) -> tuple[int, int]:
    end_time = int(datetime.now().timestamp() * 1000)
    time_deltas = {
        "1h": timedelta(hours=1),
        "2h": timedelta(hours=2),
        "5h": timedelta(hours=5),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30)
    }
    delta = time_deltas.get(time_filter, timedelta(hours=24))
    start_time = int((datetime.now() - delta).timestamp() * 1000)
    return start_time, end_time

def format_time_period(start_time: int, end_time: int) -> str:
    start_dt = datetime.fromtimestamp(start_time / 1000)
    end_dt = datetime.fromtimestamp(end_time / 1000)
    return f"{start_dt.strftime('%Y-%m-%d %H:%M:%S')} to {end_dt.strftime('%Y-%m-%d %H:%M:%S')}"

def _get_log_key(log: dict) -> str:
    """Stable deduplication key: timestamp + start of message"""
    msg = log.get('message', '')
    return f"{log.get('timestamp')}-{msg[:100]}"

def _fetch_cloudwatch_logs_sync(log_group: str, start_time: int, end_time: int, 
                                 stream_prefix: str = "", limit: int = 20000) -> List[dict]:
    """Fetch logs from CloudWatch with pagination and cross-stream filtering"""
    try:
        logs = []
        next_token = None
        
        while len(logs) < limit:
            kwargs = {
                'logGroupName': log_group,
                'startTime': start_time,
                'endTime': end_time,
                'limit': min(limit - len(logs), 1000) # Fetch in chunks
            }
            logger.debug(f"Calling filter_log_events with {kwargs}")
            if stream_prefix:
                kwargs['logStreamNamePrefix'] = stream_prefix
            if next_token:
                kwargs['nextToken'] = next_token

            response = cloudwatch_client.filter_log_events(**kwargs)
            
            events = response.get('events', [])
            for event in events:
                logs.append({
                    'timestamp': event['timestamp'],
                    'message': event['message']
                })
            
            next_token = response.get('nextToken')
            if not next_token or not events:
                break
                
        # Sort newest first
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        logger.info(f"Fetched {len(logs)} logs from CloudWatch for range {start_time}-{end_time}")
        return logs
    except Exception as e:
        logger.error(f"Error fetching CloudWatch logs: {e}", exc_info=True)
        raise e # Propagate error so usage sites know it failed

async def fetch_cloudwatch_logs(log_group: str, start_time: int, end_time: int, 
                                 stream_prefix: str = "", limit: int = 20000) -> List[dict]:
    return await run_in_thread(_fetch_cloudwatch_logs_sync, log_group, start_time, end_time, stream_prefix, limit)

# --- VectorDB Storage Functions ---

async def store_logs_in_vdb(logs: List[dict]):
    """Store new logs in Vector Database"""
    if not logs: return
    # We do this in a thread because embedding generation (Bedrock) is blocking
    await run_in_thread(vector_store.add_logs, logs)

def load_logs_from_file_sync(filename: str = "cached_logs.jsonl") -> List[dict]:
    """Retrieve the most recent logs from VectorDB instead of file"""
    try:
        logs = vector_store.get_recent_logs(limit=10000)
        logger.info(f"Loaded {len(logs)} logs from VectorDB.")
        return logs
    except Exception as e:
        logger.error(f"Error loading from VectorDB: {e}", exc_info=True)
        return []

async def load_logs_from_file(filename: str = "cached_logs.jsonl") -> List[dict]:
    return await run_in_thread(load_logs_from_file_sync, filename)

def filter_logs_by_time(logs: List[dict], time_filter: str) -> tuple[List[dict], str]:
    start_time, end_time = get_time_range(time_filter)
    filtered = [log for log in logs if start_time <= log.get("timestamp", 0) <= end_time]
    period_desc = format_time_period(start_time, end_time)
    return filtered, period_desc

# --- WebSocket & Streaming ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug(f"WebSocket send failed: {e}")
                disconnected.append(connection)
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

manager = ConnectionManager()

async def stream_cloudwatch_logs():
    """Background task to continuously fetch new logs from CloudWatch"""
    last_fetch_time = int(datetime.now().timestamp() * 1000) - 60000 # Start from 1 min ago
    
    logger.info("Live stream background task started (Incremental Storage Mode)...")
    
    while True:
        try:
            current_time = int(datetime.now().timestamp() * 1000)
            
            new_logs = await fetch_cloudwatch_logs(
                LOG_GROUP_NAME,
                last_fetch_time,
                current_time,
                LOG_STREAM_PREFIX,
                limit=100
            )
            
            if new_logs:
                # 1. Update In-Memory Cache
                async with cache_lock:
                    # new_logs from CloudWatch is newest first.
                    # We want newest logs at index 0 of the deque.
                    # appendleft adds to index 0, so we push oldest->newest to get newest at front.
                    for log in reversed(new_logs):
                        live_log_cache.appendleft(log)
                
                # 2. Persist in VectorDB
                await store_logs_in_vdb(new_logs)

                # 3. Broadcast to Clients
                for log in new_logs:
                    await manager.broadcast({
                        "type": "new_log",
                        "log": log,
                        "total_logs": len(live_log_cache),
                        "timestamp": datetime.now().isoformat()
                    })
            
            last_fetch_time = current_time
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Error in streaming task: {e}", exc_info=True)
            await asyncio.sleep(10)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down FastAPI application...")
    executor.shutdown(wait=True)
    logger.info("ThreadPoolExecutor shut down gracefully.")

@app.on_event("startup")
async def startup_event():
    # Load cached logs
    cached_logs = await load_logs_from_file()
    async with cache_lock:
        live_log_cache.extend(cached_logs) # Assuming cached_logs is sorted desc
    
    try:
        # Check if we can describe log groups, otherwise stream_cloudwatch_logs catches error
        # Just fire and forget the background task
        asyncio.create_task(stream_cloudwatch_logs())
        logger.info("Live log streaming started")
    except Exception as e:
        logger.error(f"AWS error: {e}", exc_info=True)

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        async with cache_lock:
            current_logs = list(live_log_cache)
        
        await websocket.send_json({
            "type": "initial_load",
            "logs": current_logs[:100],  # Send first 100 (newest)
            "total_logs": len(current_logs)
        })
        
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                return
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        try:
            manager.disconnect(websocket)
        except Exception as e:
            logger.debug(f"Error disconnecting: {e}")

# --- REST API Endpoints ---

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_logs(req: AnalyzeRequest, _ = Depends(validate_api_key)):
    # 1. Determine Time Range uniformly
    if req.custom_start and req.custom_end:
        start_time = req.custom_start
        end_time = req.custom_end
    else:
        start_time, end_time = get_time_range(req.time_filter or "1h")
        
    time_period = format_time_period(start_time, end_time)

    # 2 & 3. Multi-layered Retrieval
    filtered_logs = await _get_full_range_logs(start_time, end_time)

    # Multi-layered Retrieval: Memory -> VectorDB -> CloudWatch
    if has_gap_in_memory or len(filtered_logs) < 10:
        logger.info(f"Cache miss/gap for {start_time}-{end_time}. Memory Oldest: {oldest_in_memory}. Checking VectorDB...")
        
        # Check VectorDB for historical data
        vdb_logs = await run_in_thread(vector_store.get_logs_in_range, start_time, end_time)
        if vdb_logs:
            # Merge and unique using stable key
            existing_keys = {_get_log_key(l) for l in filtered_logs}
            for log in vdb_logs:
                if _get_log_key(log) not in existing_keys:
                    filtered_logs.append(log)
            filtered_logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        # Check for gap again after VDB merge
        oldest_collected = filtered_logs[-1].get("timestamp", 0) if filtered_logs else float('inf')
        has_gap_overall = (not filtered_logs) or (oldest_collected > start_time + GAP_THRESHOLD_MS)

        # Last Fallback: CloudWatch (if still sparse OR has gap)
        if has_gap_overall or len(filtered_logs) < 10: 
            logger.info(f"Data still incomplete (Gap: {has_gap_overall}, Count: {len(filtered_logs)}). Fetching from CloudWatch...")
            
            # Fetch specifically what we are missing
            # If we have some logs, we only need to fetch from start_time to the oldest_collected
            # BUT: CloudWatch filter is inclusive, and we want to be safe. 
            # Safest is to fetch the whole range if count is low, or just the missing tail if we have *some* logs.
            
            fetch_cw_start = start_time
            fetch_cw_end = end_time
            
            if filtered_logs and has_gap_overall:
                 # Optimization: Only fetch the missing tail
                 fetch_cw_end = oldest_collected
                 logger.info(f"Optimization: Fetching only missing tail {fetch_cw_start} to {fetch_cw_end}")

            fetched_logs = await fetch_cloudwatch_logs(LOG_GROUP_NAME, fetch_cw_start, fetch_cw_end, LOG_STREAM_PREFIX)
            
            # Merge results using stable key
            existing_keys = {_get_log_key(l) for l in filtered_logs}
            for log in fetched_logs:
                if _get_log_key(log) not in existing_keys:
                    filtered_logs.append(log)
            filtered_logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            # Opportunistically populate VectorDB (background task)
            if fetched_logs:
                asyncio.create_task(store_logs_in_vdb(fetched_logs))
    
    # --- "No Error Left Behind" Strategy ---
    # 1. Fetch ALL logs in the range
    all_filtered_logs = filtered_logs
    total_logs_found = len(all_filtered_logs)
    
    # 2. Extract Errors and Group them by Pattern
    parsed_all = parseLogs([RawLogEntry(l['timestamp'], l['message']) for l in all_filtered_logs])
    error_logs = [log for log in parsed_all if log.get("isError")]
    unique_error_patterns = get_unique_patterns(error_logs)
    
    # 3. Smart Context Building
    # We take: Top 10 Semantic Results + Unique Error Patterns + Most Recent 200 Logs
    MAX_RECENT = 200
    recent_logs_context = all_filtered_logs[:MAX_RECENT]
    
    # 3b. Keyword / Correlation ID Extraction
    # If the user asks for a specific ID, we MUST include it, even if it's not "recent" or "semantic".
    import re
    # naive extraction of potential IDs: 8+ alphanumeric chars
    potential_ids = set(re.findall(r'\b[A-Za-z0-9-]{8,}\b', req.input))
    
    keyword_matched_logs = []
    if potential_ids:
        logger.info(f"Extracting logs for keywords/IDs: {potential_ids}")
        # Explicitly query VectorDB for these IDs to ensure they are found even if outside the range
        for pid in potential_ids:
            # Check if we already have it in all_filtered_logs
            exists = any(log.get("correlationId") == pid for log in all_filtered_logs)
            if not exists:
                vdb_pid_logs = await run_in_thread(vector_store.get_logs_by_correlation_id, pid)
                if vdb_pid_logs:
                    keyword_matched_logs.extend(vdb_pid_logs)

        # Also search in the current time-filtered set
        for log in all_filtered_logs:
            log_str = str(log) 
            if any(pid in log_str for pid in potential_ids):
                # Ensure no duplicates if already added from VDB search
                if _get_log_key(log) not in {_get_log_key(kl) for kl in keyword_matched_logs}:
                    keyword_matched_logs.append(log)
    
    # Limit keyword logs to avoid blowout
    keyword_matched_logs = keyword_matched_logs[:50] 
    keyword_logs_json = json.dumps(keyword_matched_logs, indent=2)
    
    # Semantic Search for Historical Context (Time-Filtered)
    historical_logs = []
    historical_context = ""
    try:
        # Now uses start_time and end_time which are guaranteed to be defined
        similar_logs = vector_store.search_similar_logs(
            req.input, 
            n_results=10,
            start_time=start_time,
            end_time=end_time
        )
        if similar_logs:
            historical_logs = similar_logs
            historical_context = json.dumps(similar_logs, indent=2)
    except Exception as e:
        logger.error(f"Error fetching semantic context: {e}", exc_info=True)
    # We send the unique patterns to ensure "No Error Left Behind"
    patterns_json_str = json.dumps(unique_error_patterns, indent=2)
    recent_logs_json = json.dumps(recent_logs_context, indent=2)

    # --- DYNAMIC PROMPT BUILDING ---
    is_specific_query = len(potential_ids) > 0 or len(req.input.split()) > 3
    
    prompt = f"""You are 'Log Pulse AI', an expert SRE and system reliability agent.
Your goal is to provide a HIGHLY RELEVANT response to the user's question using the logs provided.

--- USER INTENT ---
User Question: "{req.input}"
Secondary Context (Time Period): {time_period}

--- INSTRUCTIONS ---
1. PRIORITIZE the User Question. If they ask a specific question, focus your 'summary' and 'findings' ONLY on that.
2. If the user asks a GENERAL question (e.g., "Any issues?", "What's happening?"), perform a broad scan of all patterns and anomalies.
3. If the user GREETS you, respond cordially and summarize system health in 1 sentence.
4. "NO ERROR LEFT BEHIND": I've provided UNIQUE ERROR PATTERNS found across {total_logs_found} logs. Ensure any TRULY SIGNIFICANT errors are reflected in 'findings', even if rare.

--- SYSTEM DATA ---
Total Logs in Range: {total_logs_found}
Unique Error Patterns: {len(unique_error_patterns)}
Statistical Anomalies: {json.dumps(detector.detect_anomalies(parsed_all[:1000]), indent=2)}

--- UNIQUE ERROR PATTERNS (Deduped) ---
{patterns_json_str}

{"--- SEMANTICALLY RELATED HISTORICAL LOGS ---" if historical_context else ""}
{historical_context}

{"--- DIRECT KEYWORD MATCHES (High Priority) ---" if keyword_logs_json else ""}
{keyword_logs_json}

--- MOST RECENT LOGS (Contextual) ---
{recent_logs_json}

--- OUTPUT FORMAT ---
Respond ONLY with a JSON object. No preamble.
{{
  "summary": "<Direct, detailed narrative response to the User Question. If you found a trace, explain the flow step-by-step.>",
  "findings": [
    {{
      "what": "<Short title of the issue>",
      "when": "<timestamp>",
      "why": "<Root cause analysis>",
      "how": "<Technical details/log snippet>",
      "recommendation": "<Actionable fix>"
    }}
  ]
}}
"""
    try:
        # Build message history for Bedrock
        messages = []
        if req.history:
            for msg in req.history:
                role = msg.get("role")
                content = msg.get("content")
                if role in ["user", "assistant"] and content:
                    messages.append({
                        "role": role,
                        "content": [{"text": content}]
                    })
        
        # Add the current prompt as the latest user message
        messages.append({"role": "user", "content": [{"text": prompt}]})
        
        def _call_bedrock():
            return bedrock_client.converse(
                modelId=MODEL_ID,
                messages=messages,
                inferenceConfig={"temperature": 0.2, "topP": 0.9}
            )
        response = await run_in_thread(_call_bedrock)
        llm_text = response["output"]["message"]["content"][0]["text"]
        
        # Parse JSON from LLM
        def _extract_json(text: str) -> dict:
            # 1. Strip Markdown code blocks
            clean = re.sub(r'```json\s*(.*?)\s*```', r'\1', text, flags=re.DOTALL)
            clean = clean.replace("```", "").strip()
            
            # 2. Find first { and last }
            start = clean.find('{')
            end = clean.rfind('}')
            
            if start != -1 and end != -1:
                json_str = clean[start:end+1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Try to fix common LLM mistakes like trailing commas
                    # Simple fix: remove comma before closing brace/bracket
                    json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
                    try:
                        return json.loads(json_str)
                    except:
                        pass
            return None

        analysis_result = _extract_json(llm_text)
        if not analysis_result:
            logger.warning(f"Failed to parse JSON from LLM. Raw output: {llm_text[:200]}...")
            analysis_result = {
                "summary": llm_text,
                "findings": []
            }
        
        # Ensure every finding has an ID to satisfy Pydantic model
        findings = analysis_result.get("findings", [])
        for i, finding in enumerate(findings):
            if "id" not in finding:
                finding["id"] = str(uuid.uuid4())
             
        return AnalyzeResponse(
            summary=analysis_result.get("summary", "No summary provided."),
            findings=findings,
            time_period=time_period,
            logs_analyzed=total_logs_found,
            is_live=True
        )

    except Exception as e:
        logger.error(f"Error in analyze_logs: {e}", exc_info=True)
        # Return partial results or error message
        return AnalyzeResponse(
            summary=f"Analysis failed: {str(e)}",
            findings=[], 
            time_period=time_period if 'time_period' in locals() else "Unknown", 
            logs_analyzed=total_logs_found if 'total_logs_found' in locals() else 0, 
            is_live=True
        )

@app.post("/logs/filter", response_model=LogsResponse)
async def get_filtered_logs(req: TimeFilterRequest, _ = Depends(validate_api_key)):
    logger.debug(f"Received TimeFilterRequest: {req}")
    
    # CASE 1: Custom Range (Direct Fetch)
    # We do NOT use the live_log_cache for custom ranges because they might be far in the past
    # and would pollute the contiguous "live window" cache.
    if req.custom_start and req.custom_end:
        start_time = req.custom_start
        end_time = req.custom_end
        logger.debug(f"Using custom range (Direct Fetch): {start_time} - {end_time}")
        
        try:
            # Direct fetch from CloudWatch
            logs = await fetch_cloudwatch_logs(LOG_GROUP_NAME, start_time, end_time, LOG_STREAM_PREFIX)
            logger.debug(f"Direct fetch returned {len(logs)} logs")
            
            # Store in VDB (background task)
            asyncio.create_task(store_logs_in_vdb(logs))
            
            time_period = format_time_period(start_time, end_time)
            return LogsResponse(logs=logs, time_period=time_period, total_count=len(logs), is_live=False)
            
        except Exception as e:
            logger.error(f"Error in direct fetch: {e}", exc_info=True)
            return LogsResponse(logs=[], time_period="Error", total_count=0, is_live=False)

    # CASE 2: Standard Rolling Window (Cache + Gap Fill)
    start_time, end_time = get_time_range(req.time_filter)
    logger.debug(f"Using standard range ({req.time_filter}): {start_time} - {end_time}")
    
    # Check if we need to fetch historical data to fill the "Live Cache"
    missing_history = False
    fetch_start = start_time
    fetch_end = end_time
    
    async with cache_lock:
        if not live_log_cache:
            missing_history = True
        else:
            # Check oldest log in cache (last item)
            oldest_cached = live_log_cache[-1].get("timestamp", 0)
            if oldest_cached > start_time + 60000: # Buffer of 1 min
                # We need older logs than what we have
                missing_history = True
                fetch_end = oldest_cached # Fetch up to where we have data
    
    if missing_history:
        logger.info(f"Cache miss for {req.time_filter} ({start_time}-{end_time}). Fetching history from {fetch_start} to {fetch_end}...")
        try:
            # Fetch missing logs
            new_logs = await fetch_cloudwatch_logs(LOG_GROUP_NAME, fetch_start, fetch_end, LOG_STREAM_PREFIX)
            
            if new_logs:
                # Ensure correct order (Newest -> Oldest) for cache
                new_logs.sort(key=lambda x: x['timestamp'], reverse=True) 
                
                async with cache_lock:
                    # Merge using stable key to avoid duplicates during gap filling
                    existing_keys = {_get_log_key(l) for l in live_log_cache}
                    
                    for log in new_logs:
                        if _get_log_key(log) not in existing_keys:
                            live_log_cache.append(log) 
                    
                    # Ensure total ordering is maintained (Newest -> Oldest)
                    sorted_list = sorted(list(live_log_cache), key=lambda x: x.get('timestamp', 0), reverse=True)
                    live_log_cache.clear()
                    live_log_cache.extend(sorted_list)
                
                # Also persist to VectorDB (background task)
                asyncio.create_task(store_logs_in_vdb(new_logs))
        except Exception as e:
            logger.error(f"Error auto-fetching history: {e}", exc_info=True)

    try:
        async with cache_lock:
            all_logs = list(live_log_cache)
            
        # Filter explicitly here using start/end
        filtered_logs = [log for log in all_logs if start_time <= log.get("timestamp", 0) <= end_time]
        time_period = format_time_period(start_time, end_time)
        
        return LogsResponse(logs=filtered_logs, time_period=time_period, total_count=len(filtered_logs), is_live=True)
    except Exception as e:
        logger.error(f"Error in get_filtered_logs: {e}", exc_info=True)
        return LogsResponse(logs=[], time_period="Error", total_count=0, is_live=True)

@app.post("/logs/refresh")
async def refresh_logs(time_filter: str = "24h", _ = Depends(validate_api_key)):
    start_time, end_time = get_time_range(time_filter)
    new_logs = await fetch_cloudwatch_logs(LOG_GROUP_NAME, start_time, end_time, LOG_STREAM_PREFIX)
    
    async with cache_lock:
        live_log_cache.clear()
        live_log_cache.extend(new_logs)
    
    # Save to VectorDB (background task)
    asyncio.create_task(store_logs_in_vdb(new_logs)) 
    
    return {"status": "success", "logs_fetched": len(new_logs), "time_period": format_time_period(start_time, end_time)}

@app.post("/trace/flow", response_model=TraceFlowResponse)
async def get_trace_flow(req: TraceFlowRequest, _ = Depends(validate_api_key)):
    # 1. Check Memory Cache
    async with cache_lock:
        all_logs = list(live_log_cache)
    parsed_logs = parseLogs([RawLogEntry(log['timestamp'], log['message']) for log in all_logs])
    trace_logs = [log for log in parsed_logs if log.get("correlationId") == req.correlation_id]
    
    # 2. Check VectorDB if not in memory
    if not trace_logs:
        logger.info(f"Trace {req.correlation_id} not in memory. Checking VectorDB...")
        vdb_logs = await run_in_thread(vector_store.get_logs_by_correlation_id, req.correlation_id)
        if vdb_logs:
            # logs from vdb are already raw log objects (parsed)
            trace_logs = vdb_logs

    if not trace_logs:
        return TraceFlowResponse(
            correlation_id=req.correlation_id, 
            steps=[], 
            total_duration_ms=0, 
            start_time="", 
            end_time="", 
            status="NOT_FOUND", 
            error_steps=[]
        )
    
    # Ensure they are sorted by epoch
    # Note: vdb logs have 'epoch' in metadata which becomes 'timestamp' in raw_json? 
    # Let's check logParser.py. parse_json_log sets 'epoch': entry.timestamp (int).
    trace_logs.sort(key=lambda x: x.get("epoch", x.get("timestamp", 0)))
    
    steps = []
    error_steps = []
    for idx, log in enumerate(trace_logs):
        is_error = log.get("isError", False) or (log.get("statusCode", 0) >= 400)
        # Use 'epoch' for duration calculation if available (it should be for parsed logs)
        curr_ts = log.get("epoch", 0)
        next_ts = trace_logs[idx + 1].get("epoch", 0) if idx < len(trace_logs) - 1 else None
        
        step_duration = next_ts - curr_ts if next_ts is not None else None
        
        if is_error: error_steps.append(idx)
        steps.append(TraceStep(
            id=log.get("id", str(uuid.uuid4())), 
            timestamp=log.get("timestamp", ""), 
            message=log.get("message", ""), 
            level=log.get("level", "INFO"), 
            duration_ms=step_duration, 
            is_error=is_error, 
            category=log.get("category", "OTHER"), 
            step_number=idx
        ))
    
    total_duration = trace_logs[-1].get("epoch", 0) - trace_logs[0].get("epoch", 0)
    
    return TraceFlowResponse(
        correlation_id=req.correlation_id, 
        steps=steps, 
        total_duration_ms=max(total_duration, 0), 
        start_time=trace_logs[0].get("timestamp", ""), 
        end_time=trace_logs[-1].get("timestamp", ""), 
        status="FAILURE" if error_steps else "SUCCESS", 
        error_steps=error_steps
    )

@app.get("/logs/categories")
async def get_log_categories(time_filter: str = Query("24h")):
    async with cache_lock:
        all_logs = list(live_log_cache)
    filtered_logs, time_period = filter_logs_by_time(all_logs, time_filter)
    parsed_logs = parseLogs([RawLogEntry(log['timestamp'], log['message']) for log in filtered_logs])
    categories = {}
    for log in parsed_logs:
        cat = log.get("category", "OTHER")
        if cat not in categories: categories[cat] = []
        categories[cat].append({"id": log.get("id"), "timestamp": log.get("timestamp"), "message": log.get("message"), "level": log.get("level"), "isError": log.get("isError", False), "correlationId": log.get("correlationId")})
    return {"categories": categories, "time_period": time_period, "is_live": True}

@app.get("/logs/stats")
async def get_live_stats():
    async with cache_lock:
        total = len(live_log_cache)
        oldest = live_log_cache[-1].get("timestamp") if live_log_cache else None
        newest = live_log_cache[0].get("timestamp") if live_log_cache else None
    return {"total_logs_cached": total, "cache_capacity": live_log_cache.maxlen, "oldest_log_timestamp": oldest, "newest_log_timestamp": newest, "is_streaming": True}

@app.get("/alerts/history")
async def get_alerts_history(time_filter: str = "24h", _ = Depends(validate_api_key)):
    async with cache_lock:
        all_logs = list(live_log_cache)
    filtered_logs, _ = filter_logs_by_time(all_logs, time_filter)
    parsed_logs = parseLogs([RawLogEntry(log['timestamp'], log['message']) for log in filtered_logs])
    
    anomalies = detector.detect_anomalies(parsed_logs)
    alerts = []
    for a in anomalies:
        alerts.append({
            "timestamp": a.get("timestamp"),
            "alert_type": a.get("type"),
            "message": a.get("message"),
            "severity": a.get("severity", "MEDIUM"),
            "data": a
        })
    return {"alerts": alerts}

@app.post("/config/cloudwatch")
async def update_cloudwatch_config(config: CloudWatchConfig, _ = Depends(validate_api_key)):
    global LOG_GROUP_NAME, LOG_STREAM_PREFIX
    LOG_GROUP_NAME = config.log_group_name
    LOG_STREAM_PREFIX = config.log_stream_prefix or ""
    return {"status": "success", "log_group": LOG_GROUP_NAME, "log_stream_prefix": LOG_STREAM_PREFIX}

@app.get("/health")
def health_check():
    return {"status": "healthy", "streaming": True, "cached_logs": len(live_log_cache)}