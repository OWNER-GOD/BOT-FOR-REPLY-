import os
import sys
import time
import logging
from multiprocessing import Process

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_flask():
    from app import app
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

def run_main_bot():
    import bot
    bot.main()

def run_clone_manager():
    import clone_bot_manager
    clone_bot_manager.main()

if __name__ == '__main__':
    logger.info("🚀 Starting Complete Bot System...")
    
    flask_process = Process(target=run_flask, daemon=True)
    flask_process.start()
    logger.info("✅ Flask started")
    
    clone_process = Process(target=run_clone_manager, daemon=True)
    clone_process.start()
    logger.info("✅ Clone manager started")
    
    time.sleep(2)
    
    logger.info("✅ Starting main bot...")
    run_main_bot()
