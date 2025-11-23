"""
Database Models and Schema
SQLite-based storage for test generation tasks and artifacts
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from .config import config

class DatabaseManager:
    """Manages SQLite database operations"""
    
    def __init__(self, db_path: Path = config.DB_PATH):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Test Generation Tasks Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    llm_provider TEXT NOT NULL,
                    llm_model TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    progress INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 100,
                    current_step TEXT
                )
            """)
            
            # DOM Analysis Results Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dom_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    hover_elements TEXT,
                    popup_elements TEXT,
                    page_structure TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES test_tasks(id)
                )
            """)
            
            # Generated Features Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS generated_features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    feature_type TEXT NOT NULL,
                    feature_content TEXT NOT NULL,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES test_tasks(id)
                )
            """)
            
            # Execution Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    log_level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES test_tasks(id)
                )
            """)
            
            # Configuration History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    llm_provider TEXT NOT NULL,
                    llm_model TEXT NOT NULL,
                    settings TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def create_task(self, url: str, llm_provider: str, llm_model: str) -> int:
        """Create a new test generation task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO test_tasks (url, llm_provider, llm_model, status)
                VALUES (?, ?, ?, 'pending')
            """, (url, llm_provider, llm_model))
            return cursor.lastrowid
    
    def update_task_status(self, task_id: int, status: str, 
                          progress: Optional[int] = None,
                          current_step: Optional[str] = None,
                          error_message: Optional[str] = None):
        """Update task status and progress"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = ["status = ?"]
            params = [status]
            
            if progress is not None:
                updates.append("progress = ?")
                params.append(progress)
            
            if current_step is not None:
                updates.append("current_step = ?")
                params.append(current_step)
            
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
            
            if status == 'running' and progress == 0:
                updates.append("started_at = CURRENT_TIMESTAMP")
            elif status == 'completed' or status == 'failed':
                updates.append("completed_at = CURRENT_TIMESTAMP")
            
            params.append(task_id)
            query = f"UPDATE test_tasks SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
    
    def save_dom_analysis(self, task_id: int, hover_elements: List[Dict], 
                         popup_elements: List[Dict], page_structure: Dict):
        """Save DOM analysis results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO dom_analysis (task_id, hover_elements, popup_elements, page_structure)
                VALUES (?, ?, ?, ?)
            """, (
                task_id,
                json.dumps(hover_elements),
                json.dumps(popup_elements),
                json.dumps(page_structure)
            ))
    
    def save_feature(self, task_id: int, feature_type: str, 
                    feature_content: str, file_path: Optional[str] = None):
        """Save generated Gherkin feature"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO generated_features (task_id, feature_type, feature_content, file_path)
                VALUES (?, ?, ?, ?)
            """, (task_id, feature_type, feature_content, file_path))
    
    def add_log(self, task_id: int, log_level: str, message: str, details: Optional[Dict] = None):
        """Add execution log entry"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO execution_logs (task_id, log_level, message, details)
                VALUES (?, ?, ?, ?)
            """, (task_id, log_level, message, json.dumps(details) if details else None))
    
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get task details"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM test_tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all tasks"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM test_tasks 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_task_features(self, task_id: int) -> List[Dict[str, Any]]:
        """Get generated features for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM generated_features 
                WHERE task_id = ? 
                ORDER BY created_at
            """, (task_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_task_logs(self, task_id: int) -> List[Dict[str, Any]]:
        """Get execution logs for a task"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM execution_logs 
                WHERE task_id = ? 
                ORDER BY created_at
            """, (task_id,))
            return [dict(row) for row in cursor.fetchall()]

# Global database instance
db = DatabaseManager()