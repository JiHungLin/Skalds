from skalds.worker.baseclass import BaseTaskWorker, run_before_handler, run_main_handler
from skalds.utils.logging import logger
from pydantic import BaseModel, Field, ConfigDict
import time

class MySimpleDataModel(BaseModel):
    rtsp_url: str = Field(..., description="RTSP stream URL", alias="rtspUrl")
    fix_frame: int = Field(..., description="Fix frame number", alias="fixFrame")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )

class MySimpleWorker(BaseTaskWorker[MySimpleDataModel]):
    def initialize(self, data: MySimpleDataModel) -> None:
        self.rtsp_url = data.rtsp_url
        self.fix_frame = data.fix_frame

    @run_before_handler
    def before_run(self) -> None:
        logger.info(f"Starting MyWorker with RTSP URL: {self.rtsp_url}")

    @run_main_handler
    def main_run(self) -> None:
        for _ in range(30):
            logger.info(f"Running main logic for MyWorker")
            logger.info(f"RTSP URL: {self.rtsp_url}, Fix Frame: {self.fix_frame}")
            time.sleep(1)

if __name__ == "__main__":
    my_data = MySimpleDataModel(rtsp_url="rtsp://example.com/stream", fix_frame=10)
    my_worker = MySimpleWorker()
    my_worker.initialize(my_data)
    my_worker.start()