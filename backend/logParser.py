import json
import re
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4
from urllib.parse import urlparse

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

SCHEMA_VERSION = "1.1"
INFO_SAMPLE_RATE = 1.0  # 1.0 = Keep 100% of non-critical logs, 0.0 = Keep 0%

SECURITY_PATTERNS = (
    "cgi-bin", ".git", ".aws", "php-cgi", "etc/passwd", "etc/shadow", 
    "union select", "information_schema", "sleep(", "benchmark(", 
    "<script>", "onerror=", "alert(", "eval(", "base64_decode",
    "../../", "..\\..\\", "windows/win.ini", "boot.ini",
    "; rm -rf", "& dir", "| nc ", "curl http", "wget http",
    "sqlmap", "nikto", "wpscan", "burpsuite", "gobuster"
)

# -------------------------------------------------------------------
# MODELS
# -------------------------------------------------------------------

class RawLogEntry:
    def __init__(self, timestamp: int, message: str):
        self.timestamp = timestamp
        self.message = message


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def _id() -> str:
    return str(uuid4())


def _iso(ts_ms: int) -> str:
    return datetime.utcfromtimestamp(ts_ms / 1000).isoformat()


def _safe_lower(val: Optional[str]) -> str:
    return val.lower() if isinstance(val, str) else ""


def _extract_corr_from_payload(obj: Any) -> Optional[str]:
    """
    Deep-search correlationId/requestId in payload
    """
    if isinstance(obj, dict):
        for key in ("correlationId", "requestId", "traceId", "x-correlation-id"):
            if key in obj and isinstance(obj[key], str):
                return obj[key]
        for v in obj.values():
            found = _extract_corr_from_payload(v)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _extract_corr_from_payload(item)
            if found:
                return found
    return None


def _extract_user_session(obj: Any) -> tuple[Optional[str], Optional[str]]:
    """
    Search for user/session identifiers in payload
    """
    user_id = None
    session_id = None
    
    if isinstance(obj, dict):
        # User ID patterns
        for key in ("userId", "user_id", "sub", "userEmail", "customer_id"):
            if key in obj and isinstance(obj[key], (str, int)):
                user_id = str(obj[key])
                break
        
        # Session ID patterns
        for key in ("sessionId", "session_id", "sid", "session"):
            if key in obj and isinstance(obj[key], (str, int)):
                session_id = str(obj[key])
                break
                
        if user_id and session_id:
            return user_id, session_id
            
        for v in obj.values():
            u, s = _extract_user_session(v)
            if u: user_id = u
            if s: session_id = s
            if user_id and session_id:
                break
                
    elif isinstance(obj, list):
        for item in obj:
            u, s = _extract_user_session(item)
            if u: user_id = u
            if s: session_id = s
            if user_id and session_id:
                break
                
    return user_id, session_id


def _should_sample(level: str, step_type: str) -> bool:
    if level in ("ERROR", "WARN"):
        return False
    if step_type in ("ENTRY", "EXIT"):
        return False
    return random.random() > INFO_SAMPLE_RATE  # If 1.0, random() > 1.0 is False (keep all)


# -------------------------------------------------------------------
# REGEX
# -------------------------------------------------------------------

PREFIX_REGEX = re.compile(
    r'^\[(?P<ts>.*?)\]\s*\[(?P<level>.*?)\]\s*\[(?P<app>.*?)\]\s*\[(?P<corr>.*?)\](?:\s*\[(.*?)\])?\s*(?P<msg>.*)$'
)

HTTP_REGEX = re.compile(
    r'\[(GET|POST|PUT|DELETE|PATCH)\]\s*\[(\d{3})\]\s*(\S+)\s*-\s*Completed in:\s*(-?\d+)ms'
)

ENTRY_PATTERNS = ("request received", "incoming request", "start processing")
EXIT_PATTERNS = ("completed", "response sent", "finished processing")
CALL_PATTERNS = ("make request", "calling", "sending request", "query result")


# -------------------------------------------------------------------
# STEP TYPE
# -------------------------------------------------------------------

def classify_step(level: str, msg: str, category: str) -> str:
    m = _safe_lower(msg)

    if level == "ERROR":
        return "ERROR"

    if any(p in m for p in ENTRY_PATTERNS):
        return "ENTRY"

    if any(p in m for p in EXIT_PATTERNS):
        return "EXIT"

    if category in ("EXTERNAL", "DB"):
        return "CALL"

    if any(p in m for p in CALL_PATTERNS):
        return "CALL"

    return "EVENT"


# -------------------------------------------------------------------
# PARSERS
# -------------------------------------------------------------------

def parse_json_log(entry: RawLogEntry) -> Optional[Dict[str, Any]]:
    msg = entry.message.strip()
    if not msg.startswith("{"):
        return None

    try:
        obj = json.loads(msg)
    except json.JSONDecodeError:
        return None

    response = obj.get("response", {})
    status = response.get("statusCode")

    corr = (
        obj.get("correlationId")
        or obj.get("requestId")
        or _extract_corr_from_payload(obj)
        or "UNKNOWN"
    )

    category = "HTTP" if status else "JSON"
    level = "ERROR" if status and status >= 400 else "INFO"

    step_type = classify_step(level, msg, category)
    user_id, session_id = _extract_user_session(obj)

    # IP Extraction (from message or payload)
    source_ip = None
    ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', msg)
    if ip_match:
        source_ip = ip_match.group(0)
    # Also check directly in JSON payload fields
    source_ip = source_ip or obj.get("ip") or obj.get("clientIp") or obj.get("sourceIp")

    parsed = {
        "schemaVersion": SCHEMA_VERSION,
        "id": _id(),
        "epoch": entry.timestamp,
        "timestamp": _iso(entry.timestamp),
        "level": level,
        "appName": obj.get("service", "UNKNOWN"),
        "correlationId": corr,
        "userId": user_id,
        "sessionId": session_id,
        "sourceIp": source_ip,
        "message": obj.get("message", msg),
        "isError": level == "ERROR",
        "category": category,
        "stepType": step_type,
        "statusCode": status,
        "path": response.get("path"),
        "payload": obj,
    }

    if _should_sample(level, step_type):
        return None

    return parsed


def parse_text_log(entry: RawLogEntry) -> Dict[str, Any]:
    base = {
        "schemaVersion": SCHEMA_VERSION,
        "id": _id(),
        "epoch": entry.timestamp,
        "timestamp": _iso(entry.timestamp),
        "level": "UNKNOWN",
        "appName": "UNKNOWN",
        "correlationId": "UNKNOWN",
        "message": entry.message,
        "isError": False,
        "category": "OTHER",
        "stepType": "EVENT",
    }

    match = PREFIX_REGEX.match(entry.message)
    if not match:
        return base

    d = match.groupdict()
    msg = d["msg"]

    corr = d["corr"].replace("CorrID:", "").strip()

    parsed = {
        **base,
        "level": d["level"].upper(),
        "appName": d["app"],
        "correlationId": corr,
        "message": msg,
        "isError": d["level"].upper() == "ERROR",
    }

    # HTTP
    http = HTTP_REGEX.search(msg)
    if http:
        parsed.update({
            "category": "HTTP",
            "method": http.group(1),
            "statusCode": int(http.group(2)),
            "path": http.group(3),
            "durationMs": max(int(http.group(4)), 0),
        })
        parsed["isError"] = parsed["statusCode"] >= 400

    # External
    elif "Make request:" in msg:
        parsed["category"] = "EXTERNAL"
        url = re.search(r'(https?://\S+)', msg)
        if url:
            u = urlparse(url.group(1))
            parsed["targetSystem"] = u.hostname
            parsed["path"] = u.path

    # Security
    elif any(p in msg.lower() for p in SECURITY_PATTERNS):
        parsed["category"] = "SECURITY"
        parsed["isError"] = True

    # IP Extraction for Text Logs
    ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', msg)
    if ip_match:
        parsed["sourceIp"] = ip_match.group(0)

    # User/Session extraction from Msg (if pattern exists like "User: X")
    user_match = re.search(r'User:\s*(\S+)', msg)
    if user_match:
        parsed["userId"] = user_match.group(1)

    parsed["stepType"] = classify_step(parsed["level"], msg, parsed["category"])

    if _should_sample(parsed["level"], parsed["stepType"]):
        return None

    return parsed


# -------------------------------------------------------------------
# PATTERN DEDUPLICATION ("No Error Left Behind")
# -------------------------------------------------------------------

def get_unique_patterns(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group logs by unique patterns to ensure 100% visibility of errors 
    without exceeding token limits for long-range analysis.
    """
    patterns = {}
    
    for log in logs:
        # Create a "signature" for the log
        # For HTTP: [Status] Method Path
        # For General: Level + First 50 chars of message (ignoring IDs)
        msg = log.get("message", "")
        # Mask UUIDs/Numbers to group similar errors
        msg_template = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '<UUID>', msg)
        msg_template = re.sub(r'\d+', '<NUM>', msg_template)
        
        signature = f"[{log.get('level')}] {log.get('category')} | {log.get('path', '')} | {msg_template[:100]}"
        
        if signature not in patterns:
            patterns[signature] = {
                "pattern": signature,
                "count": 0,
                "first_seen": log.get("timestamp"),
                "last_seen": log.get("timestamp"),
                "example_message": msg,
                "level": log.get("level"),
                "category": log.get("category"),
                "isError": log.get("isError", False)
            }
        
        patterns[signature]["count"] += 1
        patterns[signature]["last_seen"] = log.get("timestamp")
        
    return list(patterns.values())


# -------------------------------------------------------------------
# PUBLIC API
# -------------------------------------------------------------------

def parseLogs(raw_logs: List[RawLogEntry]) -> List[Dict[str, Any]]:
    parsed: List[Dict[str, Any]] = []

    for entry in raw_logs:
        log = parse_json_log(entry)
        if log:
            parsed.append(log)
            continue

        text_log = parse_text_log(entry)
        if text_log:
            parsed.append(text_log)

    return parsed
