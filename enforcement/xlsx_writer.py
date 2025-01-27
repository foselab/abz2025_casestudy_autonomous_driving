from pandas import DataFrame
from datetime import datetime
import os

import logging_manager

class ExcelWriter:

    def __init__(self, folder, config_columns_value):
        """
        Initialize the path where to save the .xlsx file, the columns name 
        and the value of the configuration columns (common to all rows)
        """
        self.logger = logging_manager.get_logger(__name__)
        os.makedirs(folder, exist_ok=True)
        self.file_path = folder + f"/exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        self.columns = [
            "execution_id",
            "policy_frequency [Hz]",
            "policy",
            "lane_configuration",
            "run_enforcer [True/False]",
            "enforcer_rules",
            "crash [True/False]",
            "traveled_distance [km]",
            "effective_duration [s simulation time]",
            "enforcer_interventions [#]",
            "enforcer_model_start [ms clock wall time]",
            "enforcer_model_stop [ms clock wall time]",
            "total_enforcement_execution_time [ms clock wall time]",
            "max_enforcement_execution_time [ms clock wall time]",
            "test_execution_time [ms clock wall time]"]
        self.config_columns_value = config_columns_value
        self.data = []

    def add_row(self, row):
        """
        Add a row to the table
        """
        self.data.append(self.config_columns_value + row)

    def write_xlsx(self):
        """
        Write the data to file
        """
        self.logger.info(f"Writing data to {self.file_path}")
        df = DataFrame(self.data, columns=self.columns)
        df = df.replace({True: 'True', False: 'False'}) # Ensure boolean values are always in English
        df.to_excel(self.file_path, index=False, engine='openpyxl')