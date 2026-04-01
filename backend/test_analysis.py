
import math
import statistics

def detect_anomalies(latencies):
    if not latencies or len(latencies) < 10:
        return []
    
    mean_lat = statistics.mean(latencies)
    stdev_lat = statistics.stdev(latencies) if len(latencies) > 1 else 0
    
    anomalies = []
    if stdev_lat > 0:
        for val in latencies:
            z_score = (val - mean_lat) / stdev_lat
            if z_score > 2:
                anomalies.append((val, z_score))
    return anomalies

# Test Data
normal_data = [100, 105, 98, 102, 101, 99, 100, 103, 97, 104]
outlier_data = normal_data + [500] # 500 should be anomaly

print("Testing Normal Data:")
print(detect_anomalies(normal_data)) # Should be empty or few

print("\nTesting Outlier Data:")
anomalies = detect_anomalies(outlier_data)
print(anomalies)

assert len(anomalies) > 0, "Should detect the 500ms outlier"
print("\nValidation Successful: Z-score logic works.")
