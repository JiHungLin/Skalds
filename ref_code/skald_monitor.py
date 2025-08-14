from service import RedisService, SkaldService
import time
import threading
from store import SkaldStore
from log import logger

class SkaldMonitor:
    __instance = None

    def __init__(self, duration = 5) -> None:
        if SkaldMonitor.__instance is None:
            self.__running = False
            self.__thread = None
            self.duration = duration
            SkaldMonitor.__instance = self
        else:
            raise Exception("SkaldMonitor is a singleton class")
        
    def __work(self):
        while self.__running:
            ## Do something
            new_all_skald = SkaldService.getAllSkaldHashWithUpdateTime()
            for id, update_time in new_all_skald.items():
                if not id:
                    continue
                try:
                    if id in SkaldStore.allSkalds:
                        SkaldStore.updateSkaldUpdateTime(id, int(update_time))
                    else:
                        SkaldStore.addSkald(id, int(update_time))
                except Exception as e:
                    logger.error(f"update skald {id} error: {e}")

            need_delete_skald = []
            for id in SkaldStore.allSkalds:
                if id not in new_all_skald:
                    need_delete_skald.append(id)
            for id in need_delete_skald:
                RedisService.delKeysByPattern(f"skald:{id}:*")
                SkaldStore.delSkald(id)

            time_out_skald = []
            for id, update_time in new_all_skald.items():
                if int(time.time()*1000) - int(update_time) > 10000:
                    RedisService.delKeysByPattern(f"skald:{id}:*")
                    SkaldService.delSkald(id)
                    SkaldStore.delSkald(id)
                    time_out_skald.append(id)
            for i in time_out_skald:
                new_all_skald.pop(i)

            # Update heartbeat, all-task
            for i in new_all_skald:
                new_heartbeat = SkaldService.getSkaldHeartbeatBySkaldId(i)
                new_all_task = SkaldService.getSkaldAllTasksBySkaldId(i)
                SkaldStore.updateSkaldHeartbeat(i, new_heartbeat)
                SkaldStore.updateSkaldTasks(i, new_all_task)
            time.sleep(self.duration)

    def start(self):
        if self.__running:
            return
        self.__running = True
        self.__thread = threading.Thread(target=self.__work, daemon=True)
        self.__thread.start()

    def stop(self):
        self.__running = False
        self.__thread.join()
