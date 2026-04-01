import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import unittest
from datetime import datetime, timedelta

# Mock imports BEFORE main is imported
sys.modules['boto3'] = MagicMock()
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.config'] = MagicMock()

# Import main after mocks are set up
with patch('anomaly_detector.AnomalyDetector'):
    with patch('vector_store.VectorStore'):
        import main

class TestGapDetection(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Reset main global state
        main.live_log_cache.clear()
        
        # Setup mocks on main
        main.vector_store = MagicMock()
        main.vector_store.get_logs_in_range = MagicMock(return_value=[])
        main.vector_store.search_similar_logs = MagicMock(return_value=[])
        
        main.bedrock_client = MagicMock()
        main.bedrock_client.converse = MagicMock(return_value={
            "output": {"message": {"content": [{"text": '{"summary": "test", "findings": []}'}]}}
        })
        
        main.detector = MagicMock()
        main.detector.detect_anomalies = MagicMock(return_value=[])
        
        # Common async mocks
        main.fetch_cloudwatch_logs = AsyncMock(return_value=[])
        main.store_logs_in_vdb = AsyncMock()
        
        # Use realistic "now" time for tests
        self.now_ms = int(datetime.now().timestamp() * 1000)
        main.get_time_range = MagicMock(return_value=(self.now_ms - 3600000, self.now_ms)) # 1h range

    async def test_gap_detection_partial_data(self):
        print("\nTesting Gap Detection: Partial VectorDB Data")
        
        # Request 1h: [T-3600k, T]
        start_time = self.now_ms - 3600000
        end_time = self.now_ms
        main.get_time_range.return_value = (start_time, end_time)
        
        # Cache has ONLY very recent data (last 1 min)
        # Oldest in memory: T-60k. Start: T-3600k. 
        # Gap: T-3600k to T-60k.
        main.live_log_cache.append({'timestamp': self.now_ms - 10000, 'message': 'recent', 'id': 'cache1'})
        
        # VectorDB also has only recent data (last 5 min)
        # oldest_collected = T-300k. Start: T-3600k. 
        # Gap still exists (300k > 3600k + threshold? No, T-300k > T-3600k + 300k)
        # Threshold in main.py is 5 mins (300,000ms)
        vdb_logs = [
            {'timestamp': self.now_ms - 150000, 'message': 'vdb1', 'id': 'vdb1'},
            {'timestamp': self.now_ms - 200000, 'message': 'vdb_oldest', 'id': 'vdb2'}
        ]
        # VDB call is wrapped in run_in_thread, so it must be a MAGICMOCK (synchronous), not AsyncMock
        main.vector_store.get_logs_in_range = MagicMock(return_value=vdb_logs)
        
        req = main.AnalyzeRequest(input="What is the issue?", time_filter="1h")
        await main.analyze_logs(req)
        
        # Verify CloudWatch was called because oldest_collected (T-200k) > start_time + 300k (T-3300k) is True
        # Actually: oldest_collected (T-200,000) vs start_time (T-3,600,000)
        # Is T-200k > T-3600k + 300k? Yes, T-200k > T-3300k.
        assert main.fetch_cloudwatch_logs.called, "Should fetch from CloudWatch when gap is detected"
        
        # Verify it tries to fetch the missing history
        # Optimization: fetch_cw_end = oldest_collected
        call_args = main.fetch_cloudwatch_logs.call_args
        self.assertEqual(call_args.args[1], start_time)
        self.assertEqual(call_args.args[2], vdb_logs[-1]['timestamp'])

    async def test_no_gap_sufficient_data(self):
        print("\nTesting Gap Detection: Sufficient Data")
        
        start_time = self.now_ms - 3600000
        end_time = self.now_ms
        main.get_time_range.return_value = (start_time, end_time)
        
        # VectorDB has logs covering the range (oldest is T-3550k, which is within 5m of T-3600k)
        vdb_logs = [
            {'timestamp': self.now_ms - 1000, 'message': 'newest', 'id': '1'},
            {'timestamp': start_time + 10000, 'message': 'oldest', 'id': '2'}
        ]
        # Add more to avoid "low count" trigger (< 10 logs)
        for i in range(10):
            vdb_logs.append({'timestamp': self.now_ms - 2000 - i, 'message': f'msg{i}', 'id': f'id{i}'})
        vdb_logs.sort(key=lambda x: x['timestamp'], reverse=True)
            
        main.vector_store.get_logs_in_range = MagicMock(return_value=vdb_logs)
        main.fetch_cloudwatch_logs.reset_mock()
        
        req = main.AnalyzeRequest(input="test", time_filter="1h")
        await main.analyze_logs(req)
        
        assert not main.fetch_cloudwatch_logs.called, "Should NOT fetch from CloudWatch when data covers range"

if __name__ == '__main__':
    unittest.main()
