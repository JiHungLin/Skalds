import React from 'react';
import clsx from 'clsx';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './index.module.css';

function HomepageHeader() {
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <img
          src="img/logo.svg"
          alt="Skald Logo"
          className={styles.heroLogo}
          style={{ maxWidth: '100px' }}
        />
        <Heading as="h1" className="hero__title">
          Skald
        </Heading>
        <p className="hero__subtitle">
          一個事件驅動的模組化分散式任務調度與執行系統。
        </p>
        <div>
          <a
            href="https://pypi.org/project/Skalds/"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-block',
              marginTop: '1.5rem',
            }}
          >
            <img
              src="https://img.shields.io/pypi/v/Skalds?label=PyPI%20Skalds&style=for-the-badge"
              alt="PyPI Version"
              style={{
                height: '44px',
                minWidth: '180px',
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.10)',
                background: '#fff',
                padding: '0 8px',
                objectFit: 'contain',
              }}
            />
          </a>
        </div>
      </div>
    </header>
  );
}

export default function Home() {
  const {siteConfig} = useDocusaurusContext();

  return (
    <Layout
      title="Skald - 事件驅動的模組化分散式任務調度與執行系統"
      description="Skald 是一個專為高併發後端任務管理設計的事件驅動模組化分散式任務調度與執行系統。"
    >
      <HomepageHeader />
      <main>
        <section style={{padding: '2rem 0'}}>
          <div className="container" style={{maxWidth: '900px'}}>
            <Heading as="h2">主要特色</Heading>
            <ul>
              <li>🧩 <b>模組化架構</b>：系統劃分為三大核心模組（Skald、Monitor、Dispatcher）及其支援模組，各司其職，實現高效能的分散式任務處理。</li>
              <li>🔗 <b>事件驅動通訊</b>：採用發佈/訂閱（Pub/Sub）機制的事件佇列，實現模組間的鬆耦合互動，提高系統的彈性與可擴展能力。</li>
              <li>🤖 <b>智能資源調度</b>：結合 Task Generator 與 Dispatcher 的優勢，實現基於資源感知的智能任務分配，支援容器化平台的自動擴容。</li>
              <li>📊 <b>完整的監控與管理</b>：透過 Monitor 模組提供全方位的系統監控，搭配健全的任務生命週期管理，確保系統穩定運行與資源最佳利用。</li>
            </ul>

            <Heading as="h2" style={{marginTop: '2rem'}}>系統模組總覽</Heading>
            <p>系統三大核心模組（Skald、Monitor、Dispatcher）協同運作，構建完整的任務生命週期：</p>
            <ul>
              <li>⚙️ <b>Skald (Task Generator)</b>：負責任務的初始化與生成，管理工作者註冊與配置，透過事件佇列與其他模組通訊。</li>
              <li>👁️ <b>Monitor</b>：持續監控系統狀態與效能，收集並分析資源使用情況，觸發必要的警報與通知。</li>
              <li>🚦 <b>Dispatcher</b>：基於 Monitor 提供的系統資訊進行智能調度，實現動態負載平衡，處理緊急任務優先級。</li>
            </ul>

            <Heading as="h2" style={{marginTop: '2rem'}}>適用場景</Heading>
            <ul>
              <li>🎥 AI 影像辨識與長時間運算任務，如影像分析、視訊流處理、深度學習推論等。</li>
              <li>⚡ 高併發後端服務，支援動態擴展的後端服務架構，適合負載波動大且需快速調整資源的場景。</li>
              <li>⏱️ 即時任務管理，提供靈活的任務控制能力，支持任務的暫停、取消與動態更新。</li>
            </ul>

            <Heading as="h2" style={{marginTop: '2rem'}}>快速開始</Heading>
            <p>請參考專案根目錄的 <code>README.md</code> 以獲取詳細的安裝與啟動說明。</p>
          </div>
        </section>
      </main>
    </Layout>
  );
}
