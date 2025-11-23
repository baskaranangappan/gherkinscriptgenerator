#!/usr/bin/env python3
"""
BDD Test Generator - Startup Script
Validates environment and starts the application
"""
import os
import sys
from pathlib import Path
from core import config, get_logger
logger = get_logger(__name__)
logger.info("Starting...")

def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version.split()[0]}")


def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'fastapi',
        'playwright',
        'groq',
        'openai',
        'anthropic',
        'colorlog'
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("\nInstall them with:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    print("✅ All dependencies installed")


def check_env_file():
    """Check if .env file exists"""
    env_path = Path('.env')
    if not env_path.exists():
        print("⚠️  Warning: .env file not found")
        print("\nCreate one from .env.example:")
        print("  cp .env.example .env")
        print("\nThen add your API keys to .env")

        # Check if we have API keys from environment
        has_keys = any([
            os.getenv('GROQ_API_KEY'),
            os.getenv('OPENAI_API_KEY'),
            os.getenv('ANTHROPIC_API_KEY')
        ])

        if not has_keys:
            print("\n❌ No API keys found. Please set at least one:")
            print("  - GROQ_API_KEY (recommended - free tier)")
            print("  - OPENAI_API_KEY")
            print("  - ANTHROPIC_API_KEY")
            sys.exit(1)
    else:
        print("✅ .env file found")


def check_playwright_browsers():
    """Check if Playwright browsers are installed"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Try to get browser executable path
            browser_type = p.chromium
            print("✅ Playwright browsers installed")
    except Exception as e:
        print("⚠️  Warning: Playwright browsers may not be installed")
        print("\nInstall with:")
        print("  playwright install chromium")


def create_directories():
    """Create necessary directories"""
    dirs = ['logs', 'outputs']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    print("✅ Directories created")


def display_startup_info():
    """Display startup information"""
    print("\n" + "=" * 60)
    print("🤖 BDD Test Generator - Starting...")
    print("=" * 60)
    print("\nChecking environment...")


def main():
    """Main startup routine"""
    display_startup_info()

    check_python_version()
    check_dependencies()
    check_env_file()
    check_playwright_browsers()
    create_directories()

    print("\n" + "=" * 60)
    print("✅ All checks passed! Starting application...")
    print("=" * 60 + "\n")

    # Import and run the FastAPI app
    try:
        from app import app
        from core import config, get_logger
        logger = get_logger(__name__)
        logger.info("Starting...")
        import uvicorn

        logger.info("=" * 60)
        logger.info("BDD Test Generator - Starting FastAPI Server")
        logger.info("=" * 60)
        logger.info(f"Server URL: http://{config.HOST}:{config.PORT}")
        logger.info(f"API Docs: http://{config.HOST}:{config.PORT}/api/docs")
        logger.info(f"Database: {config.DB_PATH}")
        logger.info(f"Outputs: {config.OUTPUTS_DIR}")
        logger.info(f"Logs: {config.LOGS_DIR}")
        logger.info("=" * 60)

        print(f"\n🚀 Server starting at: http://{config.HOST}:{config.PORT}")
        print(f"📊 Open your browser and navigate to the URL above")
        print(f"📚 API Documentation: http://{config.HOST}:{config.PORT}/api/docs")
        print(f"🛑 Press CTRL+C to stop the server\n")

        uvicorn.run(
            "app:app",
            host=config.HOST,
            port=config.PORT,
            reload=config.DEBUG,
            log_level=config.LOG_LEVEL.lower()
        )

    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting application: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()