import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
  title: 'Skald',
  staticDirectories: ['static'],
  tagline: '事件驅動的模組化分散式任務調度與執行系統',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://JiHungLin.github.io',
  baseUrl: '/Skald/',

  organizationName: 'JiHungLin',
  projectName: 'Skald',

  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          id: 'intro',
          path: 'docs',
          routeBasePath: 'docs',
          sidebarPath: require.resolve('./sidebars.ts'),
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/social-card.svg',
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'skald',
      logo: {
        alt: 'skald Logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          label: '核心特色',
          to: '/docs/intro',
          position: 'left',
        },
        {
          label: '快速入門',
          to: '/docs/quickstart',
          position: 'left',
        },
        {
          label: '完整手冊',
          to: '/docs/documents',
          position: 'left',
        },
        {
          label: 'Prompt',
          to: '/prompt',
          position: 'left',
        },
        {
          href: 'https://github.com/JiHungLin/Skald',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: '導覽',
          items: [
            {
              label: '核心特色',
              to: '/docs/intro',
            },
            {
              label: '快速入門',
              to: '/docs/quickstart',
            },
            {
              label: '完整手冊',
              to: '/docs/documents',
            },
          ],
        },
        {
          title: '更多',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/JiHungLin/Skald',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Skald. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
