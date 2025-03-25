import threading
from queue import Queue
import logging
import os
import time as time_module
from datetime import datetime
from zoneinfo import ZoneInfo
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from alertbot.source.startup import Initialization
from alertbot.source.constants import conditions, condition_functions

logger = logging.getLogger(__name__)

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, files, conditions, debounce_interval=1.0):

        self.files = files
        self.conditions = conditions
        self.file_paths = [os.path.abspath(task["filepath"]) for task in self.files]
        
        self.file_to_task = {task["name"]: task for task in self.files}

        self.conditions_dict = {condition["name"]: set(condition["required_files"]) for condition in self.conditions}

        self.updated_conditions = {condition["name"]: set() for condition in self.conditions}

        self.processing_queue = Queue()

        self.processing_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.processing_thread.start()

        self.lock = threading.Lock()

        self.debounce_interval = debounce_interval
        self.last_processed = {}

        self.conditions_in_queue = set()

    def on_modified(self, event):

        if event.is_directory:
            return  

        filepath = os.path.abspath(event.src_path)

        if filepath in self.file_paths:
            current_time = time_module.time()
            last_time = self.last_processed.get(filepath, 0)
            if current_time - last_time < self.debounce_interval:
                return
            else:
                self.last_processed[filepath] = current_time

            #logger.debug(f" FileChange | Note: {filepath} modified")

            try:
                task = next((t for t in self.files if os.path.abspath(t["filepath"]) == filepath), None)
                
                if task:
                    file_name = task["name"]
                    product_name, file_id = self.extract_product_and_id(file_name)
                    
                    if not product_name or not file_id:
                        logger.warning(f" FileChange | FileName: {file_name} | Note: Invalid task name")
                        return

                    with self.lock:
                        for condition in self.conditions:
                            if file_name in condition["required_files"]:
                                self.updated_conditions[condition["name"]].add(file_name)
                                #logger.debug(f" FileChange | Condition: {condition['name']} | CurrentQueue: {self.updated_conditions[condition['name']]}")
                                if self.updated_conditions[condition["name"]] == set(condition["required_files"]):
                                    if condition["name"] not in self.conditions_in_queue:
                                        self.processing_queue.put(condition)
                                        self.conditions_in_queue.add(condition["name"])
                                        #logger.debug(f" FileChange | Condition: {condition['name']} | Note: All Required Files")
                                        self.updated_conditions[condition["name"]] = set()
                                    else:
                                        pass
                                        #logger.debug(f" FileChange | Condition: {condition['name']} | Note: Already In Queue")
                else:
                    logger.warning(f" FileChange | FilePath: {event.src_path} | Note: No task found for file")
                    
            except Exception as e:
                logger.error(f" FileChange | FilePath: {event.src_path} | Note: Error Processing File: {e}")

    def extract_product_and_id(self, task_name):
        parts = task_name.split('_')
        if len(parts) < 2:
            return None, None
        return parts[0], parts[1]
    
    def is_now_in_time_range(self, start_time, end_time, now):
        if start_time <= end_time:
            return start_time <= now <= end_time
        else:
            return now >= start_time or now <= end_time
        
    def process_queue(self):
        while True:
            condition = self.processing_queue.get()
            try:
                condition_name = condition["name"]
                required_files = condition["required_files"]
                
                est = ZoneInfo('America/New_York')
                now = datetime.now(est).time()
                
                # Check if condition defines multiple time windows
                if "time_windows" in condition:
                    in_range = False
                    for window in condition["time_windows"]:
                        start_time = window.get("start_time")
                        end_time = window.get("end_time")
                        if start_time and end_time and self.is_now_in_time_range(start_time, end_time, now):
                            in_range = True
                            break
                    if not in_range:
                        #logger.debug(f" FileChange | Condition: {condition_name} | Note: Not within any specified time window")
                        continue
                else:
                    start_time = condition.get("start_time")
                    end_time = condition.get("end_time")
                    if start_time and end_time:
                        if not self.is_now_in_time_range(start_time, end_time, now):
                            #logger.debug(f" FileChange | Condition: {condition_name} | Note: Not within the time range")
                            continue
                    else:
                        pass
                        logger.warning(f" FileChange | Condition: {condition_name} | Note: No time range specified for condition. Proceeding with processing.")

                logger.debug(f" FileChange | Condition: {condition_name} | Processing: {required_files}")

                tasks = [self.file_to_task[file_name] for file_name in required_files]

                all_variables = Initialization.prep_data(tasks)
                condition_parts = condition_name.split('_')

                if len(condition_parts) != 2:
                    logger.error(f" FileChange | Condition: {condition_name} | Note: Invalid Condition Name Format")
                    continue

                function_prefix, product_name = condition_parts

                variables = all_variables.get(product_name, {})

                if not variables:
                    logger.warning(f" FileChange | Condition: {condition_name} | Note: No Variables Found For {product_name}")
                    continue

                function_class = condition_functions.get(function_prefix)
                if not function_class:
                    logger.error(f" FileChange | Condition: {condition_name} | Note: No Function Prefix Found For {function_prefix}")
                    continue

                function_instance = function_class(product_name, variables)
                function_instance.check()

                #logger.debug(f" FileChange | Condition: {condition_name} | Note: Completed Processing")
            except Exception as e:
                logger.error(f" FileChange | Condition: {condition['name']} | Note: Error processing condition: {e}")
            finally:
                with self.lock:
                    self.conditions_in_queue.discard(condition["name"])
                self.processing_queue.task_done()
