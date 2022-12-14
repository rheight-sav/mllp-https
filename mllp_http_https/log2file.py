### By Tiago Rodrigues
### Sectra Iberia, Aug 2022
### Script to manage the logging


import logging
import logging.handlers as handlers
from time import sleep
from threading import Thread
import os
import sys
import datetime


# Generates and manages the logs files
class Log2File:
    def __init__(self, file_name, folder_path, log_level_str, number_of_days_log=1):
        self.file_name = file_name
        self.folder_path = folder_path
        self.log_level_str = log_level_str
        self.number_of_days_log = number_of_days_log

    def log_level(self, arg):
        if arg == "error":
            return logging.ERROR
        elif arg == "warn":
            return logging.WARNING
        elif arg == "info":
            return logging.INFO

    def new_log(self):
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s %(message)s"
        )
        level = self.log_level(self.log_level_str)

        logger = logging.getLogger()
        logger.setLevel(level)

        filename = self.folder_path + "\\" + self.file_name
        log_handler = handlers.TimedRotatingFileHandler(filename, when='D', interval=self.number_of_days_log)
        log_handler.setFormatter(formatter)

        logger.addHandler(log_handler)


# Looks and deletes old
class LogMonitor:
    def __init__(self, number_of_days_check, folder_path):
        self.daemon = Thread(target=self.background_task, args=(number_of_days_check,), daemon=True, name='LogControl')
        self.folder_path = folder_path

    # task that runs at a fixed interval
    def background_task(self, interval_days):
        interval_sec = interval_days * 24 * 60 * 60  # Days to sec

        # run forever
        while True:
            # block for the interval
            sleep(interval_sec)

            # perform the task
            N = interval_days
            if not os.path.exists(self.folder_path):
                print("Please provide valid path")
                sys.exit(1)
            if os.path.isfile(self.folder_path):
                print("Please provide dictionary path")
                sys.exit(2)
            today = datetime.datetime.now()
            for each_file in os.listdir(self.folder_path):
                if each_file[len(each_file) - 4:len(each_file)] != ".log":
                    each_file_path = os.path.join(self.folder_path, each_file)
                    if os.path.isfile(each_file_path):
                        datetime_str = each_file[len(each_file) - 19:len(each_file)]

                        file_cre_date = datetime.datetime.strptime(datetime_str, '%Y-%m-%d_%H-%M-%S')
                        # file_cre_date = datetime.datetime.fromtimestamp(os.path.getctime(each_file_path))

                        dif_days = (today - file_cre_date).days
                        if dif_days > N:
                            os.remove(each_file_path)
                            print(each_file_path, dif_days)

    def start(self):
        self.daemon.start()
        pass
