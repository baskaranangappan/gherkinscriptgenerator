"""
LangGraph-based Test Generator Orchestrator
Replaces manual orchestration with a state machine approach
"""
import asyncio
from typing import Dict, Any, Optional, List, Annotated, TypedDict
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core import (
    config, db, get_logger,
    LLMConfig, BrowserConfig,
    BrowserAutomation,
    create_gherkin_generator
)

logger = get_logger(__name__)

# WebSocket manager reference (set by app.py)
websocket_manager = None


def set_websocket_manager(manager):
    """Set the WebSocket manager for sending updates"""
    global websocket_manager
    websocket_manager = manager


async def send_ws_update(task_id: int, update: Dict[str, Any]):
    """Send WebSocket update if manager is available"""
    if websocket_manager:
        try:
            await websocket_manager.send_update(task_id, update)
        except Exception as e:
            logger.debug(f"WebSocket update failed: {str(e)}")


# ============================================================================
# STATE DEFINITION
# ============================================================================

class WorkflowState(TypedDict):
    """State schema for the LangGraph workflow"""
    # Input parameters
    url: str
    llm_config: dict
    browser_config: dict

    # Task tracking
    task_id: Optional[int]
    status: str
    progress: int
    current_step: str
    error_message: Optional[str]

    # Browser instance (managed separately)
    browser_initialized: bool

    # Analysis results
    page_structure: Optional[Dict[str, Any]]
    hover_elements: Optional[List[Dict[str, Any]]]
    popup_elements: Optional[List[Dict[str, Any]]]

    # Generated features
    hover_features: Optional[Dict[str, Any]]
    popup_features: Optional[Dict[str, Any]]

    # Final result
    result: Optional[Dict[str, Any]]

    # Logs for debugging
    logs: Annotated[List[str], operator.add]


# ============================================================================
# NODE FUNCTIONS
# ============================================================================

async def create_task_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Create task in database"""
    try:
        url = state["url"]
        llm_config = LLMConfig(**state["llm_config"])

        task_id = db.create_task(url, llm_config.provider, llm_config.model)
        logger.info(f"Created task {task_id} for URL: {url}")

        db.update_task_status(task_id, 'running', progress=0, current_step='Initializing')
        db.add_log(task_id, 'INFO', f'Starting test generation for {url}')

        await send_ws_update(task_id, {
            'type': 'status',
            'task_id': task_id,
            'status': 'running',
            'progress': 0,
            'current_step': 'Initializing browser'
        })

        return {
            "task_id": task_id,
            "status": "running",
            "progress": 5,
            "current_step": "Task created",
            "logs": [f"Task {task_id} created for {url}"]
        }

    except Exception as e:
        error_msg = f"Failed to create task: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "failed",
            "error_message": error_msg,
            "logs": [error_msg]
        }


async def navigate_to_url_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Navigate browser to URL"""
    task_id = state["task_id"]
    url = state["url"]

    try:
        db.update_task_status(task_id, 'running', progress=15, current_step='Loading webpage')
        await send_ws_update(task_id, {
            'type': 'status',
            'task_id': task_id,
            'status': 'running',
            'progress': 15,
            'current_step': f'Loading {url}'
        })

        db.add_log(task_id, 'INFO', f'Navigating to {url}')

        return {
            "progress": 20,
            "current_step": "Page loaded",
            "browser_initialized": True,
            "logs": [f"Successfully loaded {url}"]
        }

    except Exception as e:
        error_msg = f"Failed to load URL: {str(e)}"
        logger.error(error_msg)
        db.add_log(task_id, 'ERROR', error_msg)
        return {
            "status": "failed",
            "error_message": error_msg,
            "logs": [error_msg]
        }


async def analyze_page_structure_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Analyze page structure"""
    task_id = state["task_id"]

    try:
        db.update_task_status(task_id, 'running', progress=25, current_step='Analyzing page structure')
        await send_ws_update(task_id, {
            'type': 'status',
            'task_id': task_id,
            'status': 'running',
            'progress': 25,
            'current_step': 'Analyzing page structure'
        })

        # Page structure will be set by the browser context manager
        return {
            "progress": 30,
            "current_step": "Page structure analyzed",
            "logs": ["Page structure analysis complete"]
        }

    except Exception as e:
        error_msg = f"Page structure analysis failed: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "failed",
            "error_message": error_msg,
            "logs": [error_msg]
        }


async def analyze_hover_elements_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Detect and analyze hover elements"""
    task_id = state["task_id"]

    try:
        db.update_task_status(task_id, 'running', progress=40, current_step='Detecting hover elements')
        await send_ws_update(task_id, {
            'type': 'status',
            'task_id': task_id,
            'status': 'running',
            'progress': 40,
            'current_step': 'Detecting hover elements'
        })

        # Hover elements will be set by the browser context manager
        return {
            "progress": 50,
            "current_step": "Hover elements detected",
            "logs": ["Hover element detection complete"]
        }

    except Exception as e:
        error_msg = f"Hover element detection failed: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "failed",
            "error_message": error_msg,
            "logs": [error_msg]
        }


async def analyze_popup_elements_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Detect and analyze popup elements"""
    task_id = state["task_id"]

    try:
        db.update_task_status(task_id, 'running', progress=55, current_step='Detecting popup elements')
        await send_ws_update(task_id, {
            'type': 'status',
            'task_id': task_id,
            'status': 'running',
            'progress': 55,
            'current_step': 'Detecting popup/modal elements'
        })

        # Popup elements will be set by the browser context manager
        return {
            "progress": 65,
            "current_step": "Popup elements detected",
            "logs": ["Popup element detection complete"]
        }

    except Exception as e:
        error_msg = f"Popup element detection failed: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "failed",
            "error_message": error_msg,
            "logs": [error_msg]
        }


async def generate_hover_features_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Generate Gherkin features for hover elements"""
    task_id = state["task_id"]
    url = state["url"]
    llm_config = LLMConfig(**state["llm_config"])
    hover_elements = state.get("hover_elements", [])
    page_structure = state.get("page_structure", {})

    try:
        db.update_task_status(task_id, 'running', progress=70, current_step='Generating hover test scenarios')
        await send_ws_update(task_id, {
            'type': 'status',
            'task_id': task_id,
            'status': 'running',
            'progress': 70,
            'current_step': 'Generating hover test scenarios'
        })

        gherkin_generator = create_gherkin_generator(llm_config)
        hover_features_content = gherkin_generator.generate_hover_features(
            url, hover_elements, page_structure
        )

        # Save feature file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hover_filename = f"hover_tests_{timestamp}.feature"
        hover_filepath = gherkin_generator.save_feature_file(hover_features_content, hover_filename)

        db.save_feature(task_id, 'hover', hover_features_content, str(hover_filepath))
        db.add_log(task_id, 'INFO', f'Generated hover features: {hover_filename}')

        hover_features = {
            'content': hover_features_content,
            'file': hover_filename,
            'path': str(hover_filepath)
        }

        return {
            "hover_features": hover_features,
            "progress": 80,
            "current_step": "Hover features generated",
            "logs": [f"Generated hover features: {hover_filename}"]
        }

    except Exception as e:
        error_msg = f"Hover feature generation failed: {str(e)}"
        logger.error(error_msg)
        db.add_log(task_id, 'ERROR', error_msg)
        return {
            "status": "failed",
            "error_message": error_msg,
            "logs": [error_msg]
        }


async def generate_popup_features_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Generate Gherkin features for popup elements"""
    task_id = state["task_id"]
    url = state["url"]
    llm_config = LLMConfig(**state["llm_config"])
    popup_elements = state.get("popup_elements", [])
    page_structure = state.get("page_structure", {})

    try:
        db.update_task_status(task_id, 'running', progress=85, current_step='Generating popup test scenarios')
        await send_ws_update(task_id, {
            'type': 'status',
            'task_id': task_id,
            'status': 'running',
            'progress': 85,
            'current_step': 'Generating popup test scenarios'
        })

        gherkin_generator = create_gherkin_generator(llm_config)
        popup_features_content = gherkin_generator.generate_popup_features(
            url, popup_elements, page_structure
        )

        # Save feature file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        popup_filename = f"popup_tests_{timestamp}.feature"
        popup_filepath = gherkin_generator.save_feature_file(popup_features_content, popup_filename)

        db.save_feature(task_id, 'popup', popup_features_content, str(popup_filepath))
        db.add_log(task_id, 'INFO', f'Generated popup features: {popup_filename}')

        popup_features = {
            'content': popup_features_content,
            'file': popup_filename,
            'path': str(popup_filepath)
        }

        return {
            "popup_features": popup_features,
            "progress": 95,
            "current_step": "Popup features generated",
            "logs": [f"Generated popup features: {popup_filename}"]
        }

    except Exception as e:
        error_msg = f"Popup feature generation failed: {str(e)}"
        logger.error(error_msg)
        db.add_log(task_id, 'ERROR', error_msg)
        return {
            "status": "failed",
            "error_message": error_msg,
            "logs": [error_msg]
        }


async def complete_task_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Finalize task and compile results"""
    task_id = state["task_id"]
    url = state["url"]

    try:
        db.update_task_status(task_id, 'completed', progress=100, current_step='Test generation completed')
        db.add_log(task_id, 'INFO', 'Test generation completed successfully')

        await send_ws_update(task_id, {
            'type': 'complete',
            'task_id': task_id,
            'status': 'completed',
            'progress': 100,
            'current_step': 'Test generation completed'
        })

        result = {
            'task_id': task_id,
            'status': 'completed',
            'url': url,
            'features': {
                'hover': state.get("hover_features"),
                'popup': state.get("popup_features")
            },
            'analysis': {
                'hover_elements': state.get("hover_elements", []),
                'popup_elements': state.get("popup_elements", []),
                'page_structure': state.get("page_structure", {})
            }
        }

        logger.info(f"Task {task_id} completed successfully")

        return {
            "status": "completed",
            "progress": 100,
            "current_step": "Test generation completed",
            "result": result,
            "logs": [f"Task {task_id} completed successfully"]
        }

    except Exception as e:
        error_msg = f"Task completion failed: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "failed",
            "error_message": error_msg,
            "logs": [error_msg]
        }


async def handle_error_node(state: WorkflowState) -> Dict[str, Any]:
    """Node: Handle errors and update task status"""
    task_id = state.get("task_id")
    error_message = state.get("error_message", "Unknown error")

    if task_id:
        db.update_task_status(task_id, 'failed', error_message=error_message)
        db.add_log(task_id, 'ERROR', error_message)

        await send_ws_update(task_id, {
            'type': 'error',
            'task_id': task_id,
            'status': 'failed',
            'error': error_message
        })

    logger.error(f"Workflow failed: {error_message}")

    return {
        "status": "failed",
        "logs": [f"Error handled: {error_message}"]
    }


# ============================================================================
# CONDITIONAL EDGES
# ============================================================================

def should_continue(state: WorkflowState) -> str:
    """Determine if workflow should continue or handle error"""
    if state.get("status") == "failed":
        return "handle_error"
    return "continue"


def after_create_task(state: WorkflowState) -> str:
    """Router after task creation"""
    if state.get("status") == "failed":
        return "handle_error"
    return "browser_analysis"


def after_browser_analysis(state: WorkflowState) -> str:
    """Router after browser analysis"""
    if state.get("status") == "failed":
        return "handle_error"
    return "generate_features"


def after_feature_generation(state: WorkflowState) -> str:
    """Router after feature generation"""
    if state.get("status") == "failed":
        return "handle_error"
    return "complete"


# ============================================================================
# WORKFLOW BUILDER
# ============================================================================

def build_workflow() -> StateGraph:
    """Build the LangGraph workflow"""

    # Create the graph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("create_task", create_task_node)
    workflow.add_node("browser_analysis", browser_analysis_subgraph)
    workflow.add_node("generate_hover_features", generate_hover_features_node)
    workflow.add_node("generate_popup_features", generate_popup_features_node)
    workflow.add_node("complete_task", complete_task_node)
    workflow.add_node("handle_error", handle_error_node)

    # Set entry point
    workflow.set_entry_point("create_task")

    # Add conditional edges
    workflow.add_conditional_edges(
        "create_task",
        after_create_task,
        {
            "browser_analysis": "browser_analysis",
            "handle_error": "handle_error"
        }
    )

    workflow.add_conditional_edges(
        "browser_analysis",
        after_browser_analysis,
        {
            "generate_features": "generate_hover_features",
            "handle_error": "handle_error"
        }
    )

    workflow.add_edge("generate_hover_features", "generate_popup_features")

    workflow.add_conditional_edges(
        "generate_popup_features",
        after_feature_generation,
        {
            "complete": "complete_task",
            "handle_error": "handle_error"
        }
    )

    # End states
    workflow.add_edge("complete_task", END)
    workflow.add_edge("handle_error", END)

    return workflow


async def browser_analysis_subgraph(state: WorkflowState) -> Dict[str, Any]:
    """
    Combined browser analysis node that handles the browser lifecycle
    This wraps the browser operations in a single context manager
    """
    task_id = state["task_id"]
    url = state["url"]
    browser_config = BrowserConfig(**state["browser_config"])

    try:
        # Update: Launching browser
        db.update_task_status(task_id, 'running', progress=10, current_step='Launching browser')
        await send_ws_update(task_id, {
            'type': 'status',
            'task_id': task_id,
            'status': 'running',
            'progress': 10,
            'current_step': 'Launching browser'
        })

        async with BrowserAutomation(browser_config) as browser:
            # Navigate to URL
            db.update_task_status(task_id, 'running', progress=20, current_step=f'Loading {url}')
            await send_ws_update(task_id, {
                'type': 'status',
                'task_id': task_id,
                'status': 'running',
                'progress': 20,
                'current_step': f'Loading {url}'
            })

            if not await browser.navigate_to_url(url):
                raise Exception(f"Failed to load URL: {url}")

            db.add_log(task_id, 'INFO', f'Successfully loaded {url}')

            # Analyze page structure
            db.update_task_status(task_id, 'running', progress=30, current_step='Analyzing page structure')
            await send_ws_update(task_id, {
                'type': 'status',
                'task_id': task_id,
                'status': 'running',
                'progress': 30,
                'current_step': 'Analyzing page structure'
            })

            page_structure = await browser.get_page_structure()
            db.add_log(task_id, 'INFO', f'Page structure analyzed: {page_structure.get("title", "Unknown")}')

            # Analyze hover elements
            db.update_task_status(task_id, 'running', progress=40, current_step='Detecting hover elements')
            await send_ws_update(task_id, {
                'type': 'status',
                'task_id': task_id,
                'status': 'running',
                'progress': 40,
                'current_step': 'Detecting hover elements'
            })

            hover_elements = await browser.analyze_hover_elements()
            db.add_log(task_id, 'INFO', f'Found {len(hover_elements)} hover elements',
                      {'count': len(hover_elements)})

            # Analyze popup elements
            db.update_task_status(task_id, 'running', progress=60, current_step='Detecting popup/modal elements')
            await send_ws_update(task_id, {
                'type': 'status',
                'task_id': task_id,
                'status': 'running',
                'progress': 60,
                'current_step': 'Detecting popup/modal elements'
            })

            popup_elements = await browser.analyze_popup_elements()
            db.add_log(task_id, 'INFO', f'Found {len(popup_elements)} popup elements',
                      {'count': len(popup_elements)})

        # Save analysis to database
        db.save_dom_analysis(task_id, hover_elements, popup_elements, page_structure)

        return {
            "page_structure": page_structure,
            "hover_elements": hover_elements,
            "popup_elements": popup_elements,
            "browser_initialized": True,
            "progress": 65,
            "current_step": "Browser analysis complete",
            "logs": [
                f"Page structure analyzed: {page_structure.get('title', 'Unknown')}",
                f"Found {len(hover_elements)} hover elements",
                f"Found {len(popup_elements)} popup elements"
            ]
        }

    except Exception as e:
        error_msg = f"Browser analysis error: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "failed",
            "error_message": error_msg,
            "logs": [error_msg]
        }


# ============================================================================
# ORCHESTRATOR CLASS
# ============================================================================

class TestGeneratorOrchestrator:
    """LangGraph-based orchestrator for test generation pipeline"""

    def __init__(self, llm_config: LLMConfig, browser_config: Optional[BrowserConfig] = None):
        self.llm_config = llm_config
        self.browser_config = browser_config or BrowserConfig()
        self.workflow = build_workflow()
        self.app = self.workflow.compile()
        self.task_id: Optional[int] = None

    async def generate_tests(self, url: str) -> Dict[str, Any]:
        """
        Run the test generation workflow

        Args:
            url: Website URL to analyze

        Returns:
            Dictionary with task results
        """
        try:
            # Initialize state
            initial_state: WorkflowState = {
                "url": url,
                "llm_config": self.llm_config.model_dump(),
                "browser_config": self.browser_config.model_dump(),
                "task_id": None,
                "status": "pending",
                "progress": 0,
                "current_step": "Initializing",
                "error_message": None,
                "browser_initialized": False,
                "page_structure": None,
                "hover_elements": None,
                "popup_elements": None,
                "hover_features": None,
                "popup_features": None,
                "result": None,
                "logs": []
            }

            # Run the workflow
            config = {"configurable": {"thread_id": f"task_{datetime.now().timestamp()}"}}

            final_state = None
            async for event in self.app.astream(initial_state, config):
                # Get the latest state from the event
                for node_name, node_state in event.items():
                    if node_state:
                        final_state = node_state
                        # Update task_id reference
                        if node_state.get("task_id"):
                            self.task_id = node_state["task_id"]

                        # Log progress
                        logger.debug(f"Node '{node_name}' completed. Progress: {node_state.get('progress', 0)}%")

            # Return the result
            if final_state and final_state.get("result"):
                return final_state["result"]
            elif final_state and final_state.get("status") == "failed":
                raise Exception(final_state.get("error_message", "Unknown error"))
            else:
                raise Exception("Workflow completed without result")

        except Exception as e:
            error_msg = f"Error in test generation: {str(e)}"
            logger.error(error_msg)

            if self.task_id:
                db.update_task_status(self.task_id, 'failed', error_message=error_msg)
                db.add_log(self.task_id, 'ERROR', error_msg)

                await send_ws_update(self.task_id, {
                    'type': 'error',
                    'task_id': self.task_id,
                    'status': 'failed',
                    'error': error_msg
                })

            raise


def run_test_generation(url: str, llm_config: LLMConfig,
                       browser_config: Optional[BrowserConfig] = None) -> Dict[str, Any]:
    """
    Convenience function to run test generation synchronously
    
    Args:
        url: Website URL to analyze
        llm_config: LLM configuration
        browser_config: Browser configuration (optional)
    
    Returns:
        Dictionary with results
    """
    orchestrator = TestGeneratorOrchestrator(llm_config, browser_config)
    return asyncio.run(orchestrator.generate_tests(url))