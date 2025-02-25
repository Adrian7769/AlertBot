import gspread
import os
import threading
import logging

logger = logging.getLogger(__name__)

# Take the Alert Data and Append it to google sheet, without overwriting past alert appends!