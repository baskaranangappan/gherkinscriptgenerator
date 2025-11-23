"""
FastAPI Application - BDD Test Generator
Production-grade API with WebSocket support for real-time updates
Uses LangGraph for orchestration
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict
import asyncio
from datetime import datetime
from pathlib import Path
from core import config, db, get_logger, LLMConfig, BrowserConfig, LLMFactory
from orchestrator import TestGeneratorOrchestrator, set_websocket_manager

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="BDD Test Generator",
    description="AI-Powered Gherkin Feature Generator for Hover & Popup Testing (LangGraph Edition)",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, task_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[task_id] = websocket
        logger.info(f"WebSocket connected for task {task_id}")

    def disconnect(self, task_id: int):
        if task_id in self.active_connections:
            del self.active_connections[task_id]
            logger.info(f"WebSocket disconnected for task {task_id}")

    async def send_update(self, task_id: int, message: dict):
        if task_id in self.active_connections:
            try:
                await self.active_connections[task_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket update: {str(e)}")
                self.disconnect(task_id)


manager = ConnectionManager()

# Set WebSocket manager for orchestrator
set_websocket_manager(manager)


# Pydantic models
class GenerateRequest(BaseModel):
    url: str = Field(..., description="Website URL to analyze")
    llm_provider: str = Field(default="groq", description="LLM provider")
    llm_model: Optional[str] = Field(None, description="LLM model name")
    headless: bool = Field(default=True, description="Run browser in headless mode")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=100, le=32000)
    timeout: int = Field(default=30000, ge=5000, le=120000)
    slow_mo: int = Field(default=100, ge=0, le=1000)


class TaskResponse(BaseModel):
    status: str
    task_id: int
    message: str


# Store active background tasks
active_tasks: Dict[int, asyncio.Task] = {}


# Background task for test generation using LangGraph
async def run_test_generation(task_id: int, url: str, llm_config: LLMConfig, browser_config: BrowserConfig):
    """Run test generation in background with LangGraph orchestration"""
    try:
        logger.info(f"Starting LangGraph-based generation for task {task_id}")

        orchestrator = TestGeneratorOrchestrator(llm_config, browser_config)
        orchestrator.task_id = task_id

        # Send initial update
        await manager.send_update(task_id, {
            'type': 'status',
            'task_id': task_id,
            'status': 'running',
            'progress': 0,
            'current_step': 'Initializing LangGraph workflow...'
        })

        # Run generation via LangGraph workflow
        result = await orchestrator.generate_tests(url)

        # Send completion update
        await manager.send_update(task_id, {
            'type': 'complete',
            'task_id': task_id,
            'status': 'completed',
            'progress': 100,
            'result': result
        })

        logger.info(f"Completed LangGraph generation for task {task_id}")

    except Exception as e:
        error_msg = f"LangGraph generation error for task {task_id}: {str(e)}"
        logger.error(error_msg)

        # Send error update
        await manager.send_update(task_id, {
            'type': 'error',
            'task_id': task_id,
            'status': 'failed',
            'error': str(e)
        })
    finally:
        if task_id in active_tasks:
            del active_tasks[task_id]


# Routes
@app.get("/", response_class=HTMLResponse)
async def index():
    """Main page"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    try:
        available_providers = LLMFactory.get_available_providers()

        return {
            'status': 'success',
            'providers': available_providers,
            'models': config.MODELS,
            'default_provider': config.DEFAULT_LLM_PROVIDER,
            'browser_settings': {
                'headless': True,
                'timeout': 30000,
                'viewport_width': 1920,
                'viewport_height': 1080
            },
            'orchestrator': 'LangGraph'  # Indicate we're using LangGraph
        }
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate", response_model=TaskResponse)
async def generate_tests(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Start test generation using LangGraph workflow"""
    try:
        # Validate URL
        url = request.url.strip()
        if not url.startswith('http'):
            url = 'https://' + url

        # Get LLM configuration
        llm_model = request.llm_model or config.MODELS.get(request.llm_provider, [])[0]

        llm_config = LLMConfig(
            provider=request.llm_provider,
            model=llm_model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        # Get browser configuration
        browser_config = BrowserConfig(
            headless=request.headless,
            timeout=request.timeout,
            slow_mo=request.slow_mo
        )

        # Create task
        task_id = db.create_task(url, llm_config.provider, llm_config.model)

        # Start background task with LangGraph orchestration
        task = asyncio.create_task(
            run_test_generation(task_id, url, llm_config, browser_config)
        )
        active_tasks[task_id] = task

        logger.info(f"Started LangGraph test generation task {task_id} for {url}")

        return TaskResponse(
            status='success',
            task_id=task_id,
            message='Test generation started (LangGraph)'
        )

    except Exception as e:
        logger.error(f"Error starting generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: int):
    """Get task status"""
    try:
        task = db.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail='Task not found')

        # Get features if completed
        features = []
        if task['status'] == 'completed':
            features = db.get_task_features(task_id)

        return {
            'status': 'success',
            'task': {
                'id': task['id'],
                'url': task['url'],
                'status': task['status'],
                'progress': task['progress'],
                'current_step': task['current_step'],
                'error_message': task['error_message'],
                'llm_provider': task['llm_provider'],
                'llm_model': task['llm_model'],
                'created_at': task['created_at'],
                'started_at': task['started_at'],
                'completed_at': task['completed_at']
            },
            'features': features
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks")
async def get_all_tasks(limit: int = 50):
    """Get all tasks"""
    try:
        tasks = db.get_all_tasks(limit)

        return {
            'status': 'success',
            'tasks': tasks
        }

    except Exception as e:
        logger.error(f"Error getting tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/task/{task_id}/logs")
async def get_task_logs(task_id: int):
    """Get task logs"""
    try:
        logs = db.get_task_logs(task_id)

        return {
            'status': 'success',
            'logs': logs
        }

    except Exception as e:
        logger.error(f"Error getting task logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/task/{task_id}/workflow")
async def get_workflow_info(task_id: int):
    """Get LangGraph workflow information for a task"""
    try:
        task = db.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail='Task not found')

        # Get workflow nodes that were executed
        logs = db.get_task_logs(task_id)

        workflow_steps = [
            {"name": "create_task", "status": "completed" if task['task_id'] else "pending"},
            {"name": "browser_analysis", "status": "unknown"},
            {"name": "generate_hover_features", "status": "unknown"},
            {"name": "generate_popup_features", "status": "unknown"},
            {"name": "complete_task", "status": task['status']}
        ]

        # Infer step statuses from logs
        for log in logs:
            msg = log['message'].lower()
            if 'hover elements' in msg:
                workflow_steps[1]['status'] = 'completed'
            if 'popup elements' in msg:
                workflow_steps[1]['status'] = 'completed'
            if 'hover features' in msg:
                workflow_steps[2]['status'] = 'completed'
            if 'popup features' in msg:
                workflow_steps[3]['status'] = 'completed'

        return {
            'status': 'success',
            'task_id': task_id,
            'workflow_type': 'LangGraph StateGraph',
            'steps': workflow_steps
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{task_id}/{feature_type}")
async def download_feature(task_id: int, feature_type: str):
    """Download generated feature file"""
    try:
        features = db.get_task_features(task_id)

        feature = next((f for f in features if f['feature_type'] == feature_type), None)

        if not feature or not feature['file_path']:
            raise HTTPException(status_code=404, detail='Feature file not found')

        file_path = Path(feature['file_path'])

        if not file_path.exists():
            raise HTTPException(status_code=404, detail='File does not exist')

        return FileResponse(
            path=file_path,
            media_type='text/plain',
            filename=file_path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading feature: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_tasks': len(active_tasks),
        'orchestrator': 'LangGraph'
    }


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: int):
    """WebSocket endpoint for real-time task updates"""
    await manager.connect(task_id, websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()

            # Client can request current status
            if data == "get_status":
                task = db.get_task(task_id)
                if task:
                    await websocket.send_json({
                        'type': 'status',
                        'task_id': task_id,
                        'status': task['status'],
                        'progress': task['progress'],
                        'current_step': task['current_step']
                    })
    except WebSocketDisconnect:
        manager.disconnect(task_id)


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("=" * 60)
    logger.info("BDD Test Generator - LangGraph Edition")
    logger.info("=" * 60)
    logger.info(f"Server URL: http://{config.HOST}:{config.PORT}")
    logger.info(f"API Docs: http://{config.HOST}:{config.PORT}/api/docs")
    logger.info(f"Database: {config.DB_PATH}")
    logger.info(f"Outputs: {config.OUTPUTS_DIR}")
    logger.info(f"Orchestrator: LangGraph StateGraph")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down BDD Test Generator...")
    # Cancel all active tasks
    for task_id, task in active_tasks.items():
        task.cancel()
    logger.info("Shutdown complete")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )