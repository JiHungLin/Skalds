# Skald Docusaurus Documentation Migration — Progress & Next Steps

## 已完成 (Completed)
- 清除所有 Docusaurus 預設文件、blog、markdown page
- 依據 README.md 與 @/ref_website 結構，建立新的 docs 資料夾結構與空白檔案
- modules/ 與 usage/ 子資料夾已建立，並含有 _category_.json
- architecture.jpg 已複製到 website/static/img/

## 待辦事項 (Next Steps)
- [ ] 撰寫/整理每個 docs/*.md 文件內容（依據 README.md 與專案實際情境）
- [ ] 撰寫 modules/ 及 usage/ 目錄下的各子文件內容
- [ ] 更新 website/sidebars.js 以反映新結構（如有需要可進一步優化分群）
- [ ] 更新 website/docusaurus.config.js（專案名稱、logo、favicon、navbar、footer、editUrl 等）
- [ ] 移除 website/static/img/ 下未使用的預設圖片（如 docusaurus.png 等）
- [ ] 覆蓋/設計首頁（website/src/pages/index.js）內容，介紹 Skald
- [ ] （選填）新增 Skald 相關的 blog 文章或移除 blog 功能
- [ ] 確認所有圖片、連結、sidebar 導覽皆正確
- [ ] 最終檢查與測試網站 build/deploy

---