from vector_store import VectorStore
import json
import os

def migrate():
    vstore = VectorStore()
    
    # Refresh the collection to ensure clean timestamp types
    print("Clearing existing VectorDB collection for a clean migration...")
    try:
        vstore.client.delete_collection("log_pulses")
        vstore.collection = vstore.client.create_collection(name="log_pulses", metadata={"hnsw:space": "cosine"})
    except Exception as e:
        print(f"Note: {e}")

    jsonl_path = "cached_logs.jsonl"
    
    if not os.path.exists(jsonl_path):
        print("No cached_logs.jsonl found. Nothing to migrate.")
        return

    print(f"Loading logs from {jsonl_path}...")
    logs = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))
    
    print(f"Found {len(logs)} logs. Capping migration to the most recent 2000 logs for depth and efficiency...")
    logs = logs[-2000:] # Take last 2000
    
    batch_size = 100
    for i in range(0, len(logs), batch_size):
        batch = logs[i:i + batch_size]
        vstore.add_logs(batch)
        print(f"Batch {i//batch_size + 1}: Migrated {len(batch)} logs...")

    print("Migration complete!")

if __name__ == "__main__":
    migrate()
