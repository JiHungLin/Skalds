"""Complex TaskWorker Example for Skald Framework.

This module demonstrates a more advanced implementation of a TaskWorker,
including a rich Pydantic data model, multi-phase execution, robust logging,
and error handling. It is intended as a reference for building sophisticated
workers in the Skald system.

Author: (Your Name)
"""

from typing import Optional, List
from skald.worker.baseclass import BaseTaskWorker, run_before_handler, run_main_handler
from skald.utils.logging import logger
from pydantic import BaseModel, Field, ConfigDict, ValidationError, model_validator
import time
import random


class SubTaskConfig(BaseModel):
    """Configuration for a sub-task within the complex worker."""
    name: str = Field(..., description="Name of the sub-task")
    duration: float = Field(1.0, description="Duration in seconds for this sub-task")
    fail_chance: float = Field(0.0, ge=0.0, le=1.0, description="Probability this sub-task will fail")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )


class ComplexDataModel(BaseModel):
    """Data model for ComplexWorker, supporting multiple configuration options."""
    job_id: str = Field(..., description="Unique identifier for the job", alias="jobId")
    retries: int = Field(3, ge=0, description="Number of retries allowed for failed sub-tasks")
    enable_feature_x: bool = Field(False, description="Whether to enable feature X")
    sub_tasks: List[SubTaskConfig] = Field(default_factory=list, description="List of sub-tasks to execute")
    notes: Optional[str] = Field(None, description="Optional notes for the job")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )

    @model_validator(mode='before')
    def check_subtasks(cls, values):
        if "sub_tasks" in values and not values["sub_tasks"]:
            raise ValueError("At least one sub-task must be specified.")
        return values


class ComplexWorker(BaseTaskWorker[ComplexDataModel]):
    """
    A more sophisticated TaskWorker that demonstrates:
    - Multi-phase execution
    - Sub-task management with retries
    - Feature toggling
    - Robust logging and error handling
    """

    def initialize(self, data: ComplexDataModel) -> None:
        """
        Initialize the worker with the provided data model.

        Args:
            data (ComplexDataModel): The configuration data for this worker.
        """
        self.job_id = data.job_id
        self.retries = data.retries
        self.enable_feature_x = data.enable_feature_x
        self.sub_tasks = data.sub_tasks
        self.notes = data.notes
        self._current_subtask_index = 0
        logger.info(f"[{self.job_id}] Initialized ComplexWorker with {len(self.sub_tasks)} sub-tasks.")

    @run_before_handler
    def before_run(self) -> None:
        """
        Perform pre-run checks and setup.

        Raises:
            RuntimeError: If preconditions are not met.
        """
        logger.info(f"[{self.job_id}] Running before_run checks...")
        if not self.sub_tasks:
            logger.error(f"[{self.job_id}] No sub-tasks configured. Aborting.")
            raise RuntimeError("No sub-tasks configured for this job.")

        if self.enable_feature_x:
            logger.info(f"[{self.job_id}] Feature X is enabled. Performing additional setup...")
            # Simulate feature X setup
            time.sleep(0.5)
            logger.info(f"[{self.job_id}] Feature X setup complete.")

        logger.info(f"[{self.job_id}] All pre-run checks passed.")

    @run_main_handler
    def main_run(self) -> None:
        """
        Execute the main logic of the worker, processing each sub-task with retries.

        Handles errors gracefully and logs progress.
        """
        logger.info(f"[{self.job_id}] Starting main_run with {len(self.sub_tasks)} sub-tasks.")
        for idx, subtask in enumerate(self.sub_tasks, start=1):
            attempt = 0
            success = False
            while attempt <= self.retries and not success:
                try:
                    logger.info(f"[{self.job_id}] Executing sub-task {idx}/{len(self.sub_tasks)}: '{subtask.name}' (Attempt {attempt+1})")
                    self._execute_subtask(subtask)
                    logger.info(f"[{self.job_id}] Sub-task '{subtask.name}' finished successfully.")
                    success = True
                except Exception as e:
                    attempt += 1
                    logger.warning(f"[{self.job_id}] Sub-task '{subtask.name}' failed (Attempt {attempt}): {e}")
                    if attempt > self.retries:
                        logger.error(f"[{self.job_id}] Sub-task '{subtask.name}' failed after {self.retries} retries. Aborting job.")
                        return
                    else:
                        logger.info(f"[{self.job_id}] Retrying sub-task '{subtask.name}' after delay...")
                        time.sleep(1)
        logger.info(f"[{self.job_id}] All sub-tasks finished. Job finished successfully.")

    def _execute_subtask(self, subtask: SubTaskConfig) -> None:
        """
        Simulate execution of a sub-task, with optional failure.

        Args:
            subtask (SubTaskConfig): The sub-task configuration.

        Raises:
            RuntimeError: If the sub-task fails (simulated).
        """
        logger.info(f"    [{self.job_id}] Sub-task '{subtask.name}': running for {subtask.duration:.2f}s (fail_chance={subtask.fail_chance})")
        time.sleep(subtask.duration)
        if random.random() < subtask.fail_chance:
            raise RuntimeError(f"Simulated failure in sub-task '{subtask.name}'.")

        if self.enable_feature_x:
            logger.info(f"    [{self.job_id}] Feature X logic applied to sub-task '{subtask.name}'.")

        # Simulate some result or state change
        logger.info(f"    [{self.job_id}] Sub-task '{subtask.name}' logic complete.")

if __name__ == "__main__":
    # Example usage with a complex configuration
    try:
        my_data = ComplexDataModel(
            jobId="job-12345",
            retries=2,
            enable_feature_x=True,
            sub_tasks=[
                SubTaskConfig(name="Download Data", duration=1.5, fail_chance=0.2),
                SubTaskConfig(name="Process Data", duration=2.0, fail_chance=0.1),
                SubTaskConfig(name="Upload Results", duration=1.0, fail_chance=0.0),
            ],
            notes="This is a demonstration of a complex worker."
        )
    except ValidationError as ve:
        logger.error(f"Failed to create ComplexDataModel: {ve}")
        exit(1)

    my_worker = ComplexWorker()
    my_worker.initialize(my_data)
    my_worker.start()