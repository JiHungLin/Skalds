SystemController主要有以下元件：
1. FastAPI Server: 提供HTTP接口、Dashboard、SSE通知Skald、task心跳、異常等
    - HTTP 接口提供以下內容：
        - 控制Task狀態，取消或是重新回到Created等待Dispatcher分派
        - 獲取、更新Task的Attachments內容
        - 獲取所有任務，paging
        - 所有 Skalds，如果Monitor有啟動的話，可以提供
    - Dashboard 可提供以下內容：透過另一個前端專案打包後直接使用靜態檔案host
        - Skalds 資訊，種類、連線狀態、心跳、可支援任務、當前運行所有任務
        - Task 資訊，詳細內容，可控制取消或恢復、也可更新Attachments內容
    - SSE 可讓web監聽以下內容：
        - Skal狀態、心跳、正在運行的task id與類型
        - task 的心跳、錯誤、異常
2. Monitor: 監聽Redis中的Skald與TaskWorker的所有訊息，key可以在RedisKey中有對應的表，並轉換內部資訊，包含以下，Skald的狀態只會存於記憶體中，不會進到MongoDB，任務狀態表也可於TaskLifecycleStatus中對照
    - 所有 Skalds(會含活動時間)，活動時間過舊也視為離線。
        - key為skald:hash
    - Skalds 種類，分為 node 與 edge， node可被指派任務。
        - key為skald:mode:hash
    - Skalds 心跳 -> 超過5次一樣心跳視為離線。
        - key為skald:{SkaldId}:heartbeat。
        - 先從skald:hash中拿到所有Skald，過濾過舊Skald，在逐一獲取心跳。
    - Skalds 當前負責的所有任務種類。
        - key為skald:{SkaldId}:all-task
    - TaskWorker 心跳，Normal: 0~199, Exception: -1, Cancel: -2, Complete: 200。 
        - key為task:{TaskId}:heartbeat。
        - 先從MongoDB中找出所有需要監聽心跳者，狀態為Assigning跟Running者，在逐一獲取心跳。
        - 每3秒會更新一次，拿到5次一樣心跳，視為任務中斷，需要將任務狀態改為Failed。
        - 若拿到 -1 則要將Task狀態改為 Failed
        - 若拿到 -2 則要將Task狀態改為 Cancelled
        - 如果存在Store中，但不存在MongoDB中為Assigning跟Running者，直接透過kafka發送取消事件。
    - TaskWorker 錯誤，目前TaskWorker運行的錯誤訊息，不會中斷任務，方便從外部知道目前狀況用。
        - key為task:{TaskId}:has-error
    - TaskWorker 異常，導致TaskWorler中斷的例外訊息，Taskworker本身會直接讓任務中斷，並且心跳改為-1。
        - key為task:{TaskId}:exception
3. Dispatcher: 分派需要的任務給適合的Skald執行，目前策略先以最少Task數量的Skald為優先。分派流成為，找尋適合Skald，將SkaldId更新到MongoDB Task的excutor中，並將Task的狀態改為Assigning，最後在透過kafka發布指派事件。
    - 定時從MongoDB中抓取需要分配任務，需要分派判定：狀態非Running、Cancelled、Assigning者
    - 從Store中獲取所有可用Skald，找到能支援Task且最為空閒者分派任務
4. Store：存放以上功能需要的資訊，並不會進入資料庫，目前可分為Skald跟Task的Store，


SystemController可依照參數執行不同的模組，並起使用FastAPI為基礎：
1. controller: 僅提供API
2. monitor：啟動監聽元件，提供Dashboard網頁服務
3. dispatcher：啟動分派模組

| 其中依賴關係為 dispatcher -> monitor -> controller，可依照參數來決定是否加開元件，否則只提供基本的API服務


TODO: supportedTasks, currentTasks貌似沒有同步到前端，要檢查