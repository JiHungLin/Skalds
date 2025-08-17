from typing import Dict

from skald.model.task import TaskLifecycleStatus


class TaskHeartbeatRecord: # Store Task Heartbeat Record
    def __init__(self, task_id:str, heartbeat:int = 0):
        self.task_id = task_id
        self.heartbeat_list = [heartbeat]
        self.__max_record_length = 5

    def append_heartbeat(self, heartbeat:int):
        self.heartbeat_list.append(heartbeat)
        if len(self.heartbeat_list) > self.__max_record_length:
            self.heartbeat_list.pop(0)

    def task_is_assigning(self):
        return len(self.heartbeat_list) < self.__max_record_length

    def task_is_alive(self):
        return len(set(self.heartbeat_list)) > 2

class TaskStore: # Store Running Tasks
    runningTaskHeartbeatRecords: Dict[str, TaskHeartbeatRecord] = {}

    @classmethod
    def addTask(cls, task_id:str, heartbeat:int, lifecycle_status:TaskLifecycleStatus):
        if task_id not in cls.runningTaskHeartbeatRecords:
            cls.runningTaskHeartbeatRecords[task_id] = TaskHeartbeatRecord(task_id, lifecycle_status, heartbeat)

    @classmethod
    def updateTaskHeartbeat(cls, task_id:str, heartbeat:int):
        if task_id in cls.runningTaskHeartbeatRecords:
            cls.runningTaskHeartbeatRecords[task_id].append_heartbeat(heartbeat)

    @classmethod
    def getAllTasks(cls):
        return cls.runningTaskHeartbeatRecords
    
    @classmethod
    def delTask(cls, task_id:str):
        if task_id in cls.runningTaskHeartbeatRecords:
            del cls.runningTaskHeartbeatRecords[task_id]