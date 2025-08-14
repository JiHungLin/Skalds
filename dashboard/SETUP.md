# Skald Dashboard 設置指南

## 概述

Skald Dashboard 是一個現代化的 React + TypeScript 網頁應用程式，用於監控和管理 Skald 任務和工作節點。

## 技術棧

- **前端框架**: React 18 + TypeScript
- **構建工具**: Vite
- **樣式**: Tailwind CSS
- **狀態管理**: React Query (TanStack Query)
- **表格組件**: TanStack Table
- **路由**: React Router
- **圖標**: Heroicons
- **包管理器**: pnpm (推薦) 或 yarn

## 開發環境設置

### 前置需求

- Node.js >= 18.0.0
- pnpm >= 9.0.0 (推薦) 或 yarn >= 1.22.0

### 安裝步驟

1. **安裝依賴**
   ```bash
   cd dashboard
   pnpm install
   ```

2. **啟動開發服務器**
   ```bash
   pnpm run dev
   ```
   
   開發服務器將在 `http://localhost:5173/dashboard` 啟動

3. **類型檢查**
   ```bash
   pnpm run type-check
   ```

4. **代碼檢查**
   ```bash
   pnpm run lint
   ```

## 生產環境構建

### 構建命令

```bash
pnpm run build
```

構建完成後，靜態文件將自動輸出到 `../skald/system_controller/static/dashboard/` 目錄，可直接被 FastAPI 服務器提供服務。

### 構建輸出

- `index.html` - 主 HTML 文件
- `assets/` - 包含所有 JavaScript、CSS 和其他資源文件
- 自動代碼分割和優化
- 包含 source maps 用於調試

## 項目結構

```
dashboard/
├── src/
│   ├── components/          # 可重用的 UI 組件
│   │   ├── ui/             # 基礎 UI 元素
│   │   └── Layout/         # 布局組件
│   ├── features/           # 功能特定組件
│   │   ├── dashboard/      # 主儀表板
│   │   ├── skalds/        # Skald 監控
│   │   └── tasks/         # 任務管理
│   ├── lib/               # 工具和配置
│   │   ├── api/           # API 客戶端
│   │   └── sse/           # SSE 管理器
│   ├── types/             # TypeScript 類型定義
│   └── hooks/             # 自定義 React hooks
├── public/                # 靜態資源
└── dist/                  # 構建輸出 (自動生成)
```

## 核心功能

### 1. 儀表板概覽
- 系統統計摘要
- Skald 和任務狀態概覽
- 快速操作按鈕

### 2. Skald 監控
- 實時 Skald 狀態顯示
- 支持的任務類型
- 當前任務分配情況
- 連接狀態監控

### 3. 任務管理
- 任務列表與分頁
- 狀態篩選
- 任務詳細信息
- 實時狀態更新

### 4. 實時更新 (SSE)
- Server-Sent Events 連接管理
- 自動重連機制
- Skald 狀態事件
- 任務狀態事件

## API 集成

目前使用模擬數據進行開發。當 FastAPI 後端準備就緒時，需要：

1. 更新 `src/lib/api/client.ts` 中的 API 端點
2. 移除模擬數據
3. 實現真實的 API 調用

### 預期的 API 端點

- `GET /api/skalds` - 獲取所有 Skalds
- `GET /api/skalds/{id}` - 獲取特定 Skald
- `GET /api/tasks` - 獲取任務列表 (支持分頁和篩選)
- `GET /api/tasks/{id}` - 獲取特定任務
- `PUT /api/tasks/{id}/status` - 更新任務狀態
- `PUT /api/tasks/{id}/attachments` - 更新任務附件
- `GET /api/events/skalds` - Skald SSE 事件流
- `GET /api/events/tasks` - 任務 SSE 事件流

## FastAPI 集成

### 靜態文件服務

在 FastAPI 應用中添加以下配置：

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# 掛載 dashboard 靜態文件
app.mount("/dashboard", StaticFiles(directory="static/dashboard", html=True), name="dashboard")
```

### 訪問 Dashboard

構建並部署後，可通過以下 URL 訪問：
- 開發環境: `http://localhost:5173/dashboard`
- 生產環境: `http://your-fastapi-server/dashboard`

## 開發指南

### 添加新功能

1. 在 `src/features/` 下創建新的功能目錄
2. 實現組件和相關邏輯
3. 在 `src/App.tsx` 中添加路由
4. 更新導航菜單 (如需要)

### 樣式指南

- 使用 Tailwind CSS 類名
- 遵循現有的設計系統
- 響應式設計優先
- 使用預定義的顏色主題

### 狀態管理

- 使用 React Query 管理服務器狀態
- 使用 React Context 管理客戶端狀態
- SSE 事件通過專用管理器處理

## 故障排除

### 常見問題

1. **依賴安裝失敗**
   - 確保 Node.js 版本 >= 18.0.0
   - 嘗試清除緩存: `pnpm store prune`

2. **開發服務器啟動失敗**
   - 檢查端口 5173 是否被占用
   - 檢查 TypeScript 錯誤

3. **構建失敗**
   - 運行 `pnpm run type-check` 檢查類型錯誤
   - 檢查導入路徑是否正確

4. **樣式問題**
   - 確保 Tailwind CSS 配置正確
   - 檢查 PostCSS 配置

### 調試技巧

- 使用瀏覽器開發者工具
- 檢查 Network 標籤查看 API 請求
- 使用 React Developer Tools
- 查看控制台錯誤信息

## 部署

### 自動化部署

可以設置 CI/CD 流程自動構建和部署：

```yaml
# .github/workflows/dashboard.yml
name: Dashboard CI/CD

on:
  push:
    paths:
      - 'dashboard/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: pnpm install
        working-directory: ./dashboard
      
      - name: Build
        run: pnpm run build
        working-directory: ./dashboard
```

### 手動部署

1. 運行構建命令: `pnpm run build`
2. 確認文件已輸出到 `../skald/system_controller/static/dashboard/`
3. 部署 FastAPI 應用程序
4. 通過 `/dashboard` 路徑訪問

## 維護

### 依賴更新

定期更新依賴以獲得安全修復和新功能：

```bash
pnpm update
```

### 性能監控

- 監控包大小
- 檢查加載時間
- 使用 Lighthouse 進行性能審計

## 支持

如有問題或需要幫助，請：

1. 檢查本文檔的故障排除部分
2. 查看項目的 GitHub Issues
3. 聯繫開發團隊