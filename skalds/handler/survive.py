"""
Survive Handler Module

Provides heartbeat and activity update mechanisms for distributed roles using Redis.
"""

import asyncio
import threading
from enum import Enum
from datetime import datetime
import secrets

from skalds.proxy.redis import RedisKey, RedisProxy
from skalds.utils.logging import logger
from skalds.config.systemconfig import SystemConfig

class SurviveRoleEnum(str, Enum):
    """Enumeration for survive handler roles."""
    SKALD = "skalds"
    TASKWORKER = "task_worker"
    NONE = "none"

class HeartBeat:
    """Enumeration for heartbeat statuses."""
    SUCCESS = 200
    FAILED = -1
    CANCELED = -2

class SurviveHandler:
    """
    Handles heartbeat and activity updates for distributed system roles.

    Args:
        redis_proxy (RedisProxy): Redis proxy instance.
        key (str): Redis key for heartbeat.
        role (SurviveRoleEnum): Role of the handler.
        period (int): Update period in seconds.
    """

    def __init__(
        self,
        redis_proxy: RedisProxy,
        key: str = "",
        role: SurviveRoleEnum = SurviveRoleEnum.NONE,
        period: int = 3,
    ):
        if role == SurviveRoleEnum.NONE:
            raise ValueError("The role must be SKALD or TASKWORKER!")
        self.redis_proxy = redis_proxy
        self.key = key
        self.period = period
        self._is_heartbeat_thread_running = False
        self._is_activity_thread_running = False
        self._heartbeat_thread = None
        self._activity_thread = None
        self.role = role
        logger.info(f"SurviveHandler initialized. Key: {key}, role: {role}")

    def push_success_heartbeat(self):
        """Push a successful heartbeat value to Redis."""
        self.redis_proxy.set_message(self.key, HeartBeat.SUCCESS,0, SystemConfig.REDIS_KEY_TTL)

    def push_failed_heartbeat(self):
        """Push a failed heartbeat value to Redis."""
        self.redis_proxy.set_message(self.key, HeartBeat.FAILED,0, SystemConfig.REDIS_KEY_TTL)

    def push_cancelled_heartbeat(self):
        """Push a cancelled heartbeat value to Redis."""
        self.redis_proxy.set_message(self.key, HeartBeat.CANCELED,0, SystemConfig.REDIS_KEY_TTL)

    def start_heartbeat_update(self):
        """Start the heartbeat update thread."""
        if self._heartbeat_thread is None or not self._heartbeat_thread.is_alive():
            self._is_heartbeat_thread_running = True

            def run_async_in_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.update_heartbeat_to_redis())
                loop.close()

            self._heartbeat_thread = threading.Thread(target=run_async_in_thread, daemon=True)
            self._heartbeat_thread.start()
            logger.info("Heartbeat update thread started.")
        else:
            logger.warning("Heartbeat thread is already running!")

    def stop_heartbeat_update(self):
        """Stop the heartbeat update thread."""
        self._is_heartbeat_thread_running = False
        self._heartbeat_thread = None
        logger.info("Heartbeat update thread stopped.")

    def start_activity_update(self):
        """Start the activity update thread (only for SKALD role)."""
        if self.role != SurviveRoleEnum.SKALD:
            logger.warning("Only SKALD can run activity update.")
            return

        if self._activity_thread is None or not self._activity_thread.is_alive():
            self._is_activity_thread_running = True

            def run_async_in_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.update_skald_activity_time_to_redis())
                loop.close()

            self._activity_thread = threading.Thread(target=run_async_in_thread, daemon=True)
            self._activity_thread.start()
            logger.info("Activity update thread started.")
        else:
            logger.warning("Activity thread is already running!")

    def stop_activity_update(self):
        """Stop the activity update thread."""
        self._is_activity_thread_running = False
        self._activity_thread = None
        logger.info("Activity update thread stopped.")

    async def update_heartbeat_to_redis(self):
        """Async loop to periodically update heartbeat value in Redis."""
        while self._is_heartbeat_thread_running:
            self.redis_proxy.set_message(self.key, secrets.randbelow(200), self.period+5)
            await asyncio.sleep(self.period)
        logger.info("Heartbeat update loop exited.")

    async def update_skald_activity_time_to_redis(self):
        """Async loop to periodically update skalds activity time in Redis."""
        while self._is_activity_thread_running:
            self.redis_proxy.set_hash(
                RedisKey.SKALD_LIST_HASH, 
                SystemConfig.SKALD_ID, 
                int(datetime.now().timestamp() * 1000),
                SystemConfig.REDIS_KEY_TTL
            )
            self.redis_proxy.set_hash(
                RedisKey.SKALD_MODE_LIST_HASH, 
                SystemConfig.SKALD_ID, 
                SystemConfig.SKALD_MODE,
                SystemConfig.REDIS_KEY_TTL
            )
            await asyncio.sleep(self.period)
        logger.info("Activity update loop exited.")

# End of file