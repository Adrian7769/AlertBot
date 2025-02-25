import os
import logging
import queue
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener

def setup_logging():
    LOGS_DIR = os.path.join(os.getcwd(), 'logs')
    os.makedirs(LOGS_DIR, exist_ok=True)
    LOG_FILE_PATH = os.path.join(LOGS_DIR, 'System.log')

    # Create the queue for asynchronous logging
    log_queue = queue.Queue(-1)  # Infinite size

    # Create a QueueHandler which sends log records to the queue
    queue_handler = QueueHandler(log_queue)
    queue_handler.setLevel(logging.DEBUG)

    # Get the root logger and add the queue handler to it.
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(queue_handler)

    # Create the actual handlers that will process log records:
    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Set up a QueueListener that will listen on the queue and handle records with the real handlers.
    listener = QueueListener(log_queue, file_handler, console_handler, respect_handler_level=True)
    listener.start()

    # Optionally, store the listener if you need to stop it gracefully later.
    root_logger.listener = listener
