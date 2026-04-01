import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Mock imports before importing main
sys.modules['boto3'] = MagicMock()
sys.modules['chromadb'] = MagicMock()

# Mock the specific modules used in main.py
with patch('anomaly_detector.AnomalyDetector') as MockDetector, \
     patch('vector_store.VectorStore') as MockVectorStore, \
     patch('logParser.parseLogs') as mock_parseLogs, \
     patch('logParser.get_unique_patterns') as mock_get_patterns:
     
    # Import the function to test
    import main

    # Setup Mocks
    main.live_log_cache = []
    main.vector_store = MockVectorStore()
    
    # Fix for JSON serialization of mock outputs
    main.detector.detect_anomalies = MagicMock(return_value=[])
    main.get_unique_patterns = MagicMock(return_value=[])
    main.parseLogs = MagicMock(return_value=[])
    
    # THESE ARE SYNCHRONOUS METHODS CALLED VIA run_in_thread
    main.vector_store.get_logs_in_range = MagicMock(return_value=[])
    main.vector_store.get_logs_by_correlation_id = MagicMock(return_value=[])
    main.vector_store.add_logs = MagicMock()
    
    # THESE ARE ASYNC DEFS
    main.fetch_cloudwatch_logs = AsyncMock(return_value=[])
    main.store_logs_in_vdb = AsyncMock()
    
    main.format_time_period = MagicMock(return_value="Time Period")
    main.get_time_range = MagicMock(return_value=(1000, 2000))
    
    # Mock specific calls inside analyze_logs
    main.bedrock_client = MagicMock()
    main.bedrock_client.converse = MagicMock(return_value={
        "output": {"message": {"content": [{"text": '{"summary": "test", "findings": []}'}]}}
    })

    async def test_analyze_flow():
        print("Testing analyze_logs flow...")
        
        # Scenario 1: Cache Miss / Gap
        req = main.AnalyzeRequest(input="test", time_filter="1h")
        main.live_log_cache = []
        main.get_time_range.return_value = (1000, 2000) 
        
        await main.analyze_logs(req, _="dev-secret-key")
        
        assert main.fetch_cloudwatch_logs.called, "Should have fetched from CloudWatch on empty cache"
        print("Scenario 1 Passed: Fetched from CloudWatch on empty cache.")
        
        # Scenario 2: Semantic Search Filter
        main.fetch_cloudwatch_logs.reset_mock()
        main.vector_store.search_similar_logs = MagicMock(return_value=[])
        
        await main.analyze_logs(req, _="dev-secret-key")
        
        args, kwargs = main.vector_store.search_similar_logs.call_args
        assert kwargs['start_time'] == 1000
        assert kwargs['end_time'] == 2000
        print("Scenario 2 Passed: Semantic search called with correct time range.")

    async def test_security():
        print("Testing API Key Security...")
        # Valid key
        await main.validate_api_key("dev-secret-key")
        print("Valid key passed.")
        
        # Invalid key
        try:
            await main.validate_api_key("wrong-key")
            assert False, "Should have raised HTTPException"
        except main.HTTPException as e:
            assert e.status_code == 401
            print("Invalid key correctly rejected.")

    async def main_test():
        await test_analyze_flow()
        await test_security()

    if __name__ == "__main__":
        asyncio.run(main_test())
