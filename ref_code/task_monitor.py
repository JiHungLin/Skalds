import asyncio
from entity.task import TaskLifecycleStatus
from store.skald_store import SkaldStore
from service import TaskService
import time
import threading
from store import TaskStore
from log import logger

class TaskMonitor:
    __instance = None

    def __init__(self, duration = 5) -> None:
        if TaskMonitor.__instance is None:
            self.__heartbeat_monitor_running = False
            self.__heartbeat_monitor_thread = None
            self.__task_assign_running = False
            self.__task_assign_thread = None
            self.duration = duration
            TaskMonitor.__instance = self
        else:
            raise Exception("TaskMonitor is a singleton class")
        
    def __heartbeat_monitor(self, async_loop: asyncio.AbstractEventLoop):
        while self.__heartbeat_monitor_running:
            try:
                feature = asyncio.run_coroutine_threadsafe(TaskService.getAllRunningAndAssigningTaskList(), async_loop)
                all_running_task = feature.result()
                all_running_task_ids = [i.id for i in all_running_task]
                for i in all_running_task:
                    TaskStore.addTask(i.id, 0)

                need_cancel = []
                need_remove = []
                for i, v in TaskStore.getAllTasks().items():
                    new_heartbeat = TaskService.getTaskHeartbeatByTaskId(i)
                    if new_heartbeat is None:
                        new_heartbeat = 0

                    TaskStore.updateTaskHeartbeat(i, new_heartbeat)

                    if i not in all_running_task_ids:
                        need_remove.append(i)
                        # TaskService.cancelTask(i)
                        # TaskStore.delTask(i)
                    else:
                        if v.task_is_assigning():
                            asyncio.run_coroutine_threadsafe(TaskService.updateTaskLifecycleStatus(i, TaskLifecycleStatus.Assigning), async_loop).result()
                        elif v.task_is_alive() == False:
                            need_cancel.append(i)
                        else:
                            asyncio.run_coroutine_threadsafe(TaskService.updateTaskLifecycleStatus(i, TaskLifecycleStatus.Running), async_loop).result()

                need_remove = list(set(need_remove))
                for i in need_remove:
                    TaskService.cancelTask(i)
                    TaskStore.delTask(i)        
                
                need_cancel = list(set(need_cancel))
                for i in need_cancel:
                    TaskService.cancelTask(i)
                    asyncio.run_coroutine_threadsafe(TaskService.updateTaskLifecycleStatus(i, TaskLifecycleStatus.Failed), async_loop).result()
                    TaskStore.delTask(i)
            except Exception as e:
                logger.error(e) # TODO: task_monitor.py:__heartbeat_monitor:58 - dictionary changed size during iteration
            time.sleep(self.duration)
        
    def __task_assign(self, async_loop: asyncio.AbstractEventLoop):
        while self.__task_assign_running:
            try:
                feature = asyncio.run_coroutine_threadsafe(TaskService.getNeedAssignTaskList(), async_loop)
                all_need_assign_task = feature.result()
                all_survive_skald = SkaldStore.getAllSkalds()
                all_skald_with_task_num = {}
                for i in all_survive_skald:
                    all_skald_with_task_num[i] = len(all_survive_skald[i].all_tasks)

                for i in all_need_assign_task:
                    all_skald_with_task_num = dict(sorted(all_skald_with_task_num.items(), key=lambda x: x[1]))
                    if len(all_skald_with_task_num) == 0:
                        logger.error("No skalds is available")
                        break
                    skald_id = list(all_skald_with_task_num.keys())[0]
                    asyncio.run_coroutine_threadsafe(TaskService.updateTaskExecutor(i.id, skald_id), async_loop).result()
                    asyncio.run_coroutine_threadsafe(TaskService.updateTaskLifecycleStatus(i.id, TaskLifecycleStatus.Assigning), async_loop).result()
                    TaskService.assign_task_to_skald(i)
                    all_skald_with_task_num[skald_id] += 1
            except Exception as e:
                logger.error(e)
            time.sleep(self.duration)

    def start(self, async_loop: asyncio.AbstractEventLoop):
        if not self.__heartbeat_monitor_running:            
            self.__heartbeat_monitor_running = True
            self.__heartbeat_monitor_thread = threading.Thread(target=self.__heartbeat_monitor, daemon=True, args=(async_loop,))
            self.__heartbeat_monitor_thread.start()
        if not self.__task_assign_running:
            self.__task_assign_running = True
            self.__task_assign_thread = threading.Thread(target=self.__task_assign, daemon=True, args=(async_loop,))
            self.__task_assign_thread.start()

    def stop(self):
        self.__heartbeat_monitor_running = False
        self.__task_assign_running = False
        self.__heartbeat_monitor_thread.join()
        self.__task_assign_thread.join()
