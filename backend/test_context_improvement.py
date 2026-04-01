import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import unittest
import json

# Mock imports
sys.modules['boto3'] = MagicMock()
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.config'] = MagicMock()

with patch('anomaly_detector.AnomalyDetector'), \
     patch('vector_store.VectorStore') as MockVectorStore, \
     patch('logParser.parseLogs'), \
     patch('logParser.get_unique_patterns'):
     
    import main

    class TestContextImprovement(unittest.IsolatedAsyncioTestCase):
        async def asyncSetUp(self):
            main.live_log_cache.clear()
            main.vector_store = MockVectorStore()
            main.vector_store.get_logs_in_range = AsyncMock(return_value=[])
            main.fetch_cloudwatch_logs = AsyncMock(return_value=[])
            main.store_logs_in_vdb = AsyncMock()
            
            # Key: Mock Bedrock to capture the PROMPT
            self.mock_bedrock = MagicMock()
            main.bedrock_client = self.mock_bedrock
            # Return a valid structure that main.py expects
            self.mock_bedrock.converse.return_value = {
                "output": {
                    "message": {
                        "content": [{"text": '{"summary": "test", "findings": []}'}]
                    }
                }
            }

        async def test_keyword_injection(self):
            print("\nTesting Keyword Injection...")
            
            # Setup:
            # 1. 500 logs in cache.
            # 2. Target log is at index 400 (older than top 200 "recent" logs).
            # 3. User asks for target ID.
            
            target_id = "EZ5A6x6S"
            target_log = {
                "timestamp": 1000, 
                "message": f"Critical failure for {target_id}", 
                "id": "log-400"
            }
            
            # Generate 500 dummy logs
            # Newest (index 0) to Oldest
            logs = []
            for i in range(500):
                if i == 400:
                    logs.append(target_log)
                else:
                    logs.append({"timestamp": 2000 + i, "message": f"Generic log {i}", "id": f"log-{i}"})
            
            # Sort newest first (as main.py expects)
            logs.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Put in cache
            main.live_log_cache.extend(logs)
            main.get_time_range = MagicMock(return_value=(0, 3000))
            
            # Request
            req = main.AnalyzeRequest(input=f"What happened to {target_id}?", time_filter="24h")
            
            await main.analyze_logs(req)
            
            # Verify Prompt Content
            call_args = self.mock_bedrock.converse.call_args
            # Args: modelId, messages, inferenceConfig
            messages = call_args.kwargs['messages']
            prompt_text = messages[0]['content'][0]['text']
            
            print("Verifying prompt contains target log...")
            
            # Check for the SECTION header
            assert "--- DIRECTLY RELEVANT LOGS (Keyword Match) ---" in prompt_text
            
            # Check for the specific log content
            assert target_id in prompt_text
            assert "Critical failure" in prompt_text
            
            print("SUCCESS: Target log found in prompt even though it was deep in history.")

if __name__ == '__main__':
    unittest.main()
