"""
Gardener Worker - Background process runner
Polls the gardening queue and processes AI tasks
"""
import asyncio
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from perknow.config import settings
from perknow import database as db
from perknow import gardener


class GardenerWorker:
    """
    Background worker that continuously polls the gardening queue
    and processes AI tasks one at a time.
    """
    
    def __init__(self):
        self.running = False
        self.poll_interval = settings.WORKER_POLL_INTERVAL_SECONDS
        self.max_retries = settings.MAX_RETRIES
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
    
    async def run(self):
        """Main worker loop"""
        print("🌱 Gardener Worker starting...")
        print(f"   Database: {settings.DATABASE_PATH}")
        print(f"   Ollama: {settings.OLLAMA_BASE_URL}")
        print(f"   Poll interval: {self.poll_interval}s")
        print("   Press Ctrl+C to stop\n")
        
        self.running = True
        
        while self.running:
            try:
                await self._process_next_task()
                self.consecutive_errors = 0  # Reset error counter on success
            except KeyboardInterrupt:
                print("\n🛑 Stopping Gardener Worker...")
                self.running = False
                break
            except Exception as e:
                self.consecutive_errors += 1
                print(f"❌ Worker error ({self.consecutive_errors}/{self.max_consecutive_errors}): {e}")
                
                if self.consecutive_errors >= self.max_consecutive_errors:
                    print("⚠️  Too many consecutive errors. Stopping worker.")
                    self.running = False
                    break
                
                # Wait before retrying
                await asyncio.sleep(self.poll_interval * 2)
    
    async def _process_next_task(self):
        """Process the next pending task from the queue"""
        # Get next pending task
        task = db.get_pending_task()
        
        if not task:
            # No pending tasks, wait and try again
            print(f"⏳ No pending tasks. Sleeping for {self.poll_interval}s...", end="\r")
            await asyncio.sleep(self.poll_interval)
            return
        
        print(f"\n📝 Processing task {task['id']}: {task['operation']} for note {task['note_id']}")
        
        # Mark as processing
        db.update_task_status(task["id"], "processing")
        
        # Get the gardener
        g = gardener.get_gardener()
        
        # Try processing with retries
        for attempt in range(1, self.max_retries + 1):
            try:
                result = await g.process_task(task)
                
                # Mark as completed
                db.update_task_status(task["id"], "completed", result=result)
                
                # Print result summary
                if result.get("skipped"):
                    print(f"   ⏭️  Skipped: {result.get('reason', 'Unknown')}")
                elif result.get("success"):
                    print(f"   ✅ Success: {self._summarize_result(task['operation'], result)}")
                else:
                    print(f"   ⚠️  Completed with issues: {result.get('error', 'Unknown issue')}")
                
                return  # Success, exit retry loop
                
            except Exception as e:
                error_msg = str(e)
                print(f"   ❌ Attempt {attempt}/{self.max_retries} failed: {error_msg}")
                
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"   ⏳ Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    # All retries exhausted
                    db.update_task_status(
                        task["id"], 
                        "failed", 
                        error_message=error_msg
                    )
                    print(f"   💥 Task {task['id']} failed after {self.max_retries} attempts")
    
    def _summarize_result(self, operation: str, result: dict) -> str:
        """Create a human-readable summary of the result"""
        if operation == "extract_title":
            return f"Title: '{result.get('title', 'N/A')}'"
        elif operation == "generate_embedding":
            return f"Embedding dimension: {result.get('embedding_dim', 'N/A')}"
        elif operation == "find_similar":
            return f"Found {result.get('similar_notes_found', 0)} similar notes"
        elif operation == "suggest_links":
            return f"Created {len(result.get('links_created', []))} links"
        elif operation == "suggest_tags":
            tags = [t['tag'] for t in result.get('tags', [])]
            return f"Tags: {', '.join(tags) if tags else 'None'}"
        else:
            return "Completed"
    
    def stop(self):
        """Signal the worker to stop"""
        self.running = False


async def main():
    """Entry point"""
    # Ensure database is initialized
    db.init_database()
    
    # Create and run worker
    worker = GardenerWorker()
    
    try:
        await worker.run()
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)
    
    print("👋 Gardener Worker stopped.")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
