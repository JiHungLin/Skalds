from typing import Dict, List


class TaskItem:
    def __init__(self, id, type):
        self.id = id
        self.type = type

class SlaveData:
    def __init__(self, id, update_time):
        self.id = id
        self.update_time = update_time
        self.heartbeat = 0
        self.all_tasks: List[TaskItem] = []

    def update_time(self):
        return self.update_time
    
    def update_heartbeat(self, new_heartbeat):
        self.heartbeat = new_heartbeat

    def update_tasks(self, new_tasks):
        self.all_tasks = new_tasks

class SlaveStore:
    allSlaves: Dict[str, SlaveData] = {}

    @classmethod
    def addSlave(cls, id, update_time):
        skald = SlaveData(id, update_time)
        cls.allSlaves[id] = skald
    
    @classmethod
    def updateSlaveUpdateTime(cls, id, new_update_time):
        if id in cls.allSlaves:
            cls.allSlaves[id].update_time = new_update_time

    @classmethod
    def updateSlaveHeartbeat(cls, id, new_heartbeat):
        if id in cls.allSlaves:
            cls.allSlaves[id].update_heartbeat(new_heartbeat)

    @classmethod
    def updateSlaveTasks(cls, id, new_tasks):
        if id in cls.allSlaves:
            cls.allSlaves[id].update_tasks(new_tasks)
    
    @classmethod
    def getAllSlaves(cls):
        return cls.allSlaves
    
    @classmethod
    def delSlave(cls, id):
        if id in cls.allSlaves:
            del cls.allSlaves[id]