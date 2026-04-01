import numpy as np
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AnomalyDetector:
    def __init__(self, latency_threshold_z=2.5, error_rate_threshold=0.1):
        self.latency_threshold_z = latency_threshold_z
        self.error_rate_threshold = error_rate_threshold

    def detect_anomalies(self, parsed_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        anomalies = []
        
        # 1. Latency Anomalies
        latencies = [log.get('durationMs') for log in parsed_logs if log.get('durationMs') is not None]
        if len(latencies) > 10:
            mean_latency = np.mean(latencies)
            std_latency = np.std(latencies)
            
            if std_latency > 0:
                for log in parsed_logs:
                    duration = log.get('durationMs')
                    if duration is not None:
                        z_score = (duration - mean_latency) / std_latency
                        if z_score > self.latency_threshold_z:
                            anomalies.append({
                                "type": "LATENCY_SPIKE",
                                "severity": "HIGH" if z_score > 4 else "MEDIUM",
                                "message": f"Latency spike detected: {duration}ms (Avg: {mean_latency:.1f}ms)",
                                "timestamp": log.get('timestamp'),
                                "id": log.get('id'),
                                "correlationId": log.get('correlationId')
                            })

        # 2. Error Rate Spikes (Time-windowed)
        # Groups logs by 5-minute intervals
        windows = {}
        for log in parsed_logs:
            try:
                # Simple windowing by 5 mins
                ts = datetime.fromisoformat(log.get('timestamp').replace('Z', ''))
                window_key = ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)
                if window_key not in windows:
                    windows[window_key] = {"total": 0, "errors": 0}
                
                windows[window_key]["total"] += 1
                if log.get('isError'):
                    windows[window_key]["errors"] += 1
            except ValueError as e:
                logger.debug(f"Error parsing timestamp: {e}")
                continue

        for window, stats in windows.items():
            error_rate = stats["errors"] / stats["total"] if stats["total"] > 0 else 0
            if error_rate > self.error_rate_threshold and stats["total"] > 5:
                anomalies.append({
                    "type": "ERROR_RATE_SPIKE",
                    "severity": "CRITICAL" if error_rate > 0.5 else "HIGH",
                    "message": f"High error rate ({error_rate*100:.1f}%) in 5min window starting {window.strftime('%H:%M')}",
                    "timestamp": window.isoformat(),
                    "total_requests": stats["total"],
                    "error_count": stats["errors"]
                })

        # 3. Security Anomalies
        anomalies.extend(self.detect_security_anomalies(parsed_logs))

        return anomalies

    def detect_security_anomalies(self, parsed_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        security_anomalies = []
        
        # 1. Brute Force Detection (By IP and CorrelationId)
        auth_failures = {} # key: sender (IP or CorrID)
        for log in parsed_logs:
            if log.get('statusCode') in (401, 403):
                sender = log.get('sourceIp') or log.get('correlationId') or 'UNKNOWN'
                if sender not in auth_failures:
                    auth_failures[sender] = []
                auth_failures[sender].append(log)
        
        for sender, logs in auth_failures.items():
            if len(logs) > 5:
                security_anomalies.append({
                    "type": "BRUTE_FORCE_ATTEMPT",
                    "severity": "CRITICAL" if len(logs) > 15 else "HIGH",
                    "message": f"Potential brute force detected: {len(logs)} auth failures from {sender}",
                    "timestamp": logs[0].get('timestamp'),
                    "id": logs[0].get('id'),
                    "sourceIp": logs[0].get('sourceIp'),
                    "correlationId": logs[0].get('correlationId'),
                    "count": len(logs)
                })

        # 2. Resource Scanning (By IP and CorrelationId)
        scan_attempts = {}
        for log in parsed_logs:
            if log.get('statusCode') == 404:
                sender = log.get('sourceIp') or log.get('correlationId') or 'UNKNOWN'
                if sender not in scan_attempts:
                    scan_attempts[sender] = set()
                scan_attempts[sender].add(log.get('path', 'UNKNOWN'))
        
        for sender, paths in scan_attempts.items():
            if len(paths) > 5:
                security_anomalies.append({
                    "type": "RESOURCE_SCANNING",
                    "severity": "HIGH",
                    "message": f"Resource scanning detected: {len(paths)} unique 404 paths from {sender}",
                    "timestamp": datetime.now().isoformat(),
                    "sourceIp": sender if '.' in sender else None,
                    "correlationId": sender if '-' in sender else None,
                    "unique_paths": len(paths)
                })

        # 3. DoS Detection (Traffic Volume + Error/Latency)
        windows = {}
        for log in parsed_logs:
            ts = log.get('timestamp')
            if not ts: continue
            try:
                # 1-minute windowing
                dt = datetime.fromisoformat(ts.replace('Z', ''))
                win = dt.replace(second=0, microsecond=0)
                if win not in windows:
                    windows[win] = {"total": 0, "slow": 0, "error": 0}
                
                windows[win]["total"] += 1
                if (log.get('durationMs') or 0) > 500: windows[win]["slow"] += 1
                if log.get('isError'): windows[win]["error"] += 1
            except: continue
        
        for win, stats in windows.items():
            # Threshold: > 100 requests/min + high error/latency
            if stats["total"] > 100 and (stats["error"] / stats["total"] > 0.2 or stats["slow"] / stats["total"] > 0.3):
                security_anomalies.append({
                    "type": "DOS_ATTEMPT",
                    "severity": "CRITICAL" if stats["total"] > 300 else "HIGH",
                    "message": f"Potential Denial of Service detected: {stats['total']} req/min with high failures",
                    "timestamp": win.isoformat(),
                    "total_requests": stats["total"],
                    "error_rate": f"{(stats['error']/stats['total'])*100:.1f}%"
                })

        # 4. Sensitive Path Access
        security_logs = [log for log in parsed_logs if log.get('category') == 'SECURITY']
        if security_logs:
            security_anomalies.append({
                "type": "HACK_ATTEMPT",
                "severity": "CRITICAL" if len(security_logs) > 3 else "HIGH",
                "message": f"Detected {len(security_logs)} malicious patterns (SQLi/XSS/Traversal)",
                "timestamp": security_logs[0].get('timestamp'),
                "count": len(security_logs),
                "examples": [log.get('message')[:100] for log in security_logs[:3]]
            })

        return security_anomalies
