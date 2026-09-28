# 前端硬编码颜色逐文件清单（审计明细）

- 生成日期：2026-09-23
- 审计基准：commit `4faa051`（本次颜色统一改动前的 dev 基线）
- 扫描范围：`agent-frontend/src`（`.vue` / `.css` / `.js`）
- 排除：`src/design-system/tokens.css`（`--xc-*` token 定义源，值字面量合法）
- 匹配模式：`#[0-9a-fA-F]{3,8}`、`rgb(` / `rgba(`、`hsl(` / `hsla(`
- 统计：33 个文件 / 224 行

## 一、汇总（按行数降序）

| 文件 | hex | rgb/rgba | hsl/hsla | 合计 |
| --- | ---: | ---: | ---: | ---: |
| src\views\login.vue | 12 | 43 | 0 | 55 |
| src\views\home\components\WelcomeScene.vue | 0 | 53 | 0 | 53 |
| src\views\index-map\components\ProvinceIndexDetail.vue | 18 | 11 | 0 | 24 |
| src\components\TrialQuotaBadge.vue | 0 | 11 | 0 | 11 |
| src\views\home\components\ResultCard.vue | 2 | 5 | 0 | 7 |
| src\views\tie-line\components\TieLineFilterBar.vue | 0 | 6 | 0 | 6 |
| src\views\tie-line\components\TieLineDetailPanel.vue | 0 | 5 | 0 | 5 |
| src\views\tie-line\components\MapToolbar.vue | 0 | 5 | 0 | 5 |
| src\views\policy-market\components\ConsultationResult.vue | 0 | 5 | 0 | 5 |
| src\components\ReadonlyResultCard.vue |  | 3 | 0 | 4 |
| src\views\policy-market\components\MarketPulse.vue | 3 |  | 0 | 4 |
| src\views\policy-market\index.vue | 4 | 0 | 0 | 4 |
| src\views\tie-line\components\ChinaTieLineMap.vue | 0 | 4 | 0 | 4 |
| src\views\policy-market\components\ConsultationComposer.vue |  | 2 | 0 | 3 |
| src\layout\index.vue | 2 |  | 0 | 3 |
| src\views\tie-line\components\TieLinePowerTrend.vue | 0 | 3 | 0 | 3 |
| src\views\tie-line\components\tieLineMapOption.js |  | 2 | 0 | 3 |
| src\views\index-map\components\ChinaIndexMap.vue |  |  | 0 | 2 |
| src\views\index-map\components\IndexMapToolbar.vue | 2 | 0 | 0 | 2 |
| src\views\index-map\components\IndexRankingList.vue | 0 | 2 | 0 | 2 |
| src\components\TrialQuotaNotice.vue |  |  | 0 | 2 |
| src\views\tie-line\components\TieLineStatsBar.vue | 0 | 2 | 0 | 2 |
| src\views\home\index.vue | 0 | 2 | 0 | 2 |
| src\views\tie-line\index.vue | 0 | 2 | 0 | 2 |
| src\views\calculation-ledger\index.vue | 2 | 0 | 0 | 2 |
| src\views\index-map\index.vue | 0 | 2 | 0 | 2 |
| src\views\calculation-result\index.vue |  | 0 | 0 | 1 |
| src\styles\report-print.css | 0 |  | 0 | 1 |
| src\views\home\components\RevenueDonut.vue | 0 |  | 0 | 1 |
| src\views\index-map\components\IndexPeriodSelect.vue |  | 0 | 0 | 1 |
| src\views\index-map\components\IndexSummaryCards.vue | 0 |  | 0 | 1 |
| src\views\public\calculation-share.vue |  | 0 | 0 | 1 |
| src\views\home\components\ShareDialog.vue |  | 0 | 0 | 1 |

## 二、逐文件明细

### src\views\login.vue（55 行）

- `src\views\login.vue:315` — `  background: #050b1a;`
- `src\views\login.vue:322` — `  background-color: #050b1a;`
- `src\views\login.vue:324` — `    linear-gradient(90deg, rgba(4, 10, 26, 0.35), rgba(4, 10, 26, 0.05) 42%, rgba(4, 10, 26, 0.28)),`
- `src\views\login.vue:332` — `  --cyan: #35d0ff;`
- `src\views\login.vue:333` — `  --blue: #2f7bff;`
- `src\views\login.vue:334` — `  --blue-light: #4d9bff;`
- `src\views\login.vue:335` — `  --text: #eaf3ff;`
- `src\views\login.vue:336` — `  --muted: rgba(206, 224, 250, 0.72);`
- `src\views\login.vue:337` — `  --faint: rgba(206, 224, 250, 0.5);`
- `src\views\login.vue:338` — `  --panel-bg: rgba(11, 27, 56, 0.55);`
- `src\views\login.vue:339` — `  --line: rgba(96, 150, 240, 0.2);`
- `src\views\login.vue:340` — `  --shadow: 0 18px 60px rgba(2, 10, 30, 0.4);`
- `src\views\login.vue:385` — `  filter: drop-shadow(0 0 16px rgba(47, 123, 255, 0.55));`
- `src\views\login.vue:398` — `  color: rgba(224, 236, 255, 0.82);`
- `src\views\login.vue:418` — `  color: rgba(224, 236, 255, 0.86);`
- `src\views\login.vue:426` — `  border-right: 1px solid rgba(255, 255, 255, 0.16);`
- `src\views\login.vue:445` — `  border: 1px solid rgba(255, 255, 255, 0.16);`
- `src\views\login.vue:447` — `  background: rgba(255, 255, 255, 0.03);`
- `src\views\login.vue:471` — `  text-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);`
- `src\views\login.vue:480` — `  color: rgba(226, 238, 255, 0.9);`
- `src\views\login.vue:488` — `  text-shadow: 0 0 20px rgba(53, 208, 255, 0.4);`
- `src\views\login.vue:536` — `  background: linear-gradient(160deg, rgba(53, 208, 255, 0.24), rgba(47, 123, 255, 0.14));`
- `src\views\login.vue:537` — `  border: 1px solid rgba(77, 155, 255, 0.42);`
- `src\views\login.vue:545` — `  filter: drop-shadow(0 0 10px rgba(53, 208, 255, 0.5));`
- `src\views\login.vue:549` — `  color: rgba(237, 245, 255, 0.96);`
- `src\views\login.vue:607` — `  color: rgba(206, 224, 250, 0.7);`
- `src\views\login.vue:615` — `  border: 1px solid rgba(96, 150, 240, 0.22);`
- `src\views\login.vue:618` — `  background: rgba(6, 16, 38, 0.5);`
- `src\views\login.vue:626` — `  border-color: rgba(77, 155, 255, 0.6);`
- `src\views\login.vue:627` — `  box-shadow: 0 0 0 3px rgba(47, 123, 255, 0.14);`
- `src\views\login.vue:631` — `  color: rgba(206, 224, 250, 0.42);`
- `src\views\login.vue:643` — `  color: rgba(206, 224, 250, 0.72);`
- `src\views\login.vue:668` — `  border: 1px solid rgba(96, 150, 240, 0.28);`
- `src\views\login.vue:671` — `  background: rgba(6, 16, 38, 0.5);`
- `src\views\login.vue:677` — `  border-color: rgba(77, 155, 255, 0.55);`
- `src\views\login.vue:689` — `  border-color: rgba(255, 118, 132, 0.55);`
- `src\views\login.vue:699` — `  color: rgba(255, 150, 162, 0.92);`
- `src\views\login.vue:742` — `  background: linear-gradient(90deg, #3d8bff, #2f6fe6);`
- `src\views\login.vue:743` — `  color: #fff;`
- `src\views\login.vue:748` — `  box-shadow: 0 12px 30px rgba(47, 123, 255, 0.32);`
- `src\views\login.vue:754` — `  box-shadow: 0 16px 38px rgba(47, 123, 255, 0.46);`
- `src\views\login.vue:776` — `  background: linear-gradient(90deg, transparent, rgba(96, 150, 240, 0.36));`
- `src\views\login.vue:780` — `  background: linear-gradient(90deg, rgba(96, 150, 240, 0.36), transparent);`
- `src\views\login.vue:793` — `  color: rgba(224, 236, 255, 0.84);`
- `src\views\login.vue:802` — `  filter: drop-shadow(0 0 10px rgba(47, 123, 255, 0.45));`
- `src\views\login.vue:870` — `  color: rgba(237, 245, 255, 0.96);`
- `src\views\login.vue:888` — `  color: #8d5cff;`
- `src\views\login.vue:892` — `  color: #1ecf9a;`
- `src\views\login.vue:896` — `  color: #f0ae3d;`
- `src\views\login.vue:900` — `  color: #39b9ff;`
- `src\views\login.vue:912` — `  color: rgba(224, 236, 255, 0.72);`
- `src\views\login.vue:928` — `  background: rgba(77, 155, 255, 0.7);`
- `src\views\login.vue:929` — `  box-shadow: 0 0 10px rgba(77, 155, 255, 0.8);`
- `src\views\login.vue:934` — `  color: rgba(206, 224, 250, 0.56);`
- `src\views\login.vue:939` — `  color: rgba(206, 224, 250, 0.68);`

### src\views\home\components\WelcomeScene.vue（53 行）

- `src\views\home\components\WelcomeScene.vue:396` — `  --scene-transparent: rgba(0, 0, 0, 0);`
- `src\views\home\components\WelcomeScene.vue:397` — `  --scene-mask-black: rgb(0, 0, 0);`
- `src\views\home\components\WelcomeScene.vue:398` — `  --scene-mask-white: rgb(255, 255, 255);`
- `src\views\home\components\WelcomeScene.vue:399` — `  --scene-atmosphere-core: rgba(0, 176, 185, 0.105);`
- `src\views\home\components\WelcomeScene.vue:400` — `  --scene-atmosphere-mid: rgba(34, 177, 253, 0.025);`
- `src\views\home\components\WelcomeScene.vue:401` — `  --scene-core-center: rgba(12, 36, 57, 0.28);`
- `src\views\home\components\WelcomeScene.vue:402` — `  --scene-core-edge: rgba(3, 12, 27, 0.04);`
- `src\views\home\components\WelcomeScene.vue:403` — `  --scene-metal-front-hi: rgba(84, 111, 136, 0.25);`
- `src\views\home\components\WelcomeScene.vue:404` — `  --scene-metal-front-lo: rgba(16, 29, 47, 0.74);`
- `src\views\home\components\WelcomeScene.vue:405` — `  --scene-metal-side-hi: rgba(34, 61, 82, 0.50);`
- `src\views\home\components\WelcomeScene.vue:406` — `  --scene-metal-side-lo: rgba(8, 18, 33, 0.86);`
- `src\views\home\components\WelcomeScene.vue:407` — `  --scene-metal-top-hi: rgba(104, 139, 160, 0.24);`
- `src\views\home\components\WelcomeScene.vue:408` — `  --scene-metal-top-lo: rgba(21, 42, 60, 0.58);`
- `src\views\home\components\WelcomeScene.vue:409` — `  --scene-panel-hi: rgba(25, 91, 123, 0.45);`
- `src\views\home\components\WelcomeScene.vue:410` — `  --scene-panel-lo: rgba(10, 29, 58, 0.78);`
- `src\views\home\components\WelcomeScene.vue:411` — `  --scene-sweep: rgba(122, 224, 255, 0.38);`
- `src\views\home\components\WelcomeScene.vue:412` — `  --scene-ring-band-hi: rgba(38, 106, 133, 0.72);`
- `src\views\home\components\WelcomeScene.vue:413` — `  --scene-ring-band-mid: rgba(12, 42, 66, 0.92);`
- `src\views\home\components\WelcomeScene.vue:414` — `  --scene-ring-band-lo: rgba(36, 29, 79, 0.70);`
- `src\views\home\components\WelcomeScene.vue:415` — `  --scene-cyan-line: rgba(0, 240, 253, 0.55);`
- `src\views\home\components\WelcomeScene.vue:416` — `  --scene-violet-line: rgba(154, 100, 255, 0.50);`
- `src\views\home\components\WelcomeScene.vue:417` — `  --scene-particle-input: rgba(92, 210, 239, 0.72);`
- `src\views\home\components\WelcomeScene.vue:418` — `  --scene-particle-output: rgba(183, 155, 255, 0.74);`
- `src\views\home\components\WelcomeScene.vue:419` — `  --scene-particle-output-accent: rgba(96, 205, 248, 0.48);`
- `src\views\home\components\WelcomeScene.vue:448` — `.ir-scene-grid-node circle:first-child { fill: rgba(8, 20, 38, 0.72); stroke: var(--xc-border-accent); stroke-width: 1; }`
- `src\views\home\components\WelcomeScene.vue:459` — `.ir-scene-device-shadow { fill: rgba(0, 0, 0, 0.34); }`
- `src\views\home\components\WelcomeScene.vue:460` — `.ir-scene-device-shadow--storage { fill: rgba(0, 0, 0, 0.46); }`
- `src\views\home\components\WelcomeScene.vue:462` — `.ir-scene-wind-tower { fill: url(#ir-scene-metal-front); stroke: rgba(167, 202, 220, 0.34); stroke-width: 1; }`
- `src\views\home\components\WelcomeScene.vue:464` — `.ir-scene-wind-nacelle { fill: url(#ir-scene-metal-top); stroke: rgba(180, 214, 229, 0.34); stroke-width: 1; }`
- `src\views\home\components\WelcomeScene.vue:470` — `.ir-scene-wind-rotor path { fill: rgba(111, 153, 177, 0.34); stroke: rgba(184, 217, 232, 0.38); stroke-width: 0.9; }`
- `src\views\home\components\WelcomeScene.vue:471` — `.ir-scene-wind-rotor circle { fill: rgba(13, 37, 57, 0.95); stroke: var(--xc-brand-cyan-2); stroke-width: 1.2; }`
- `src\views\home\components\WelcomeScene.vue:474` — `.ir-scene-solar-support { fill: none; stroke: rgba(133, 169, 187, 0.28); stroke-width: 2; }`
- `src\views\home\components\WelcomeScene.vue:475` — `.ir-scene-solar-panel polygon { fill: url(#ir-scene-panel); stroke: rgba(93, 196, 222, 0.48); stroke-width: 1.1; }`
- `src\views\home\components\WelcomeScene.vue:476` — `.ir-scene-solar-panel path { fill: none; stroke: rgba(93, 186, 215, 0.22); stroke-width: 0.75; }`
- `src\views\home\components\WelcomeScene.vue:488` — `.ir-scene-cabinet-top { fill: url(#ir-scene-metal-top); stroke: rgba(139, 185, 204, 0.32); stroke-width: 1; }`
- `src\views\home\components\WelcomeScene.vue:489` — `.ir-scene-cabinet-side { fill: url(#ir-scene-metal-side); stroke: rgba(83, 139, 165, 0.35); stroke-width: 1; }`
- `src\views\home\components\WelcomeScene.vue:490` — `.ir-scene-cabinet-front { fill: url(#ir-scene-metal-front); stroke: rgba(139, 185, 204, 0.46); stroke-width: 1.1; }`
- `src\views\home\components\WelcomeScene.vue:493` — `.ir-scene-cabinet-vents path { fill: none; stroke: rgba(151, 193, 210, 0.23); stroke-width: 0.8; }`
- `src\views\home\components\WelcomeScene.vue:494` — `.ir-scene-cabinet-modules path { fill: rgba(4, 16, 29, 0.46); stroke: rgba(83, 152, 178, 0.28); stroke-width: 0.75; }`
- `src\views\home\components\WelcomeScene.vue:495` — `.ir-scene-cabinet-control { fill: rgba(0, 176, 185, 0.16); stroke: rgba(0, 240, 253, 0.42); stroke-width: 0.7; }`
- `src\views\home\components\WelcomeScene.vue:499` — `.ir-scene-input-path { stroke: rgba(66, 166, 195, 0.20); stroke-width: 0.9; stroke-dasharray: 3 9; }`
- `src\views\home\components\WelcomeScene.vue:500` — `.ir-scene-input-path--storage { stroke: rgba(0, 240, 253, 0.29); stroke-width: 1.2; }`
- `src\views\home\components\WelcomeScene.vue:503` — `.ir-scene-apparatus-shadow { fill: rgba(0, 0, 0, 0.25); filter: url(#ir-scene-soft-glow); }`
- `src\views\home\components\WelcomeScene.vue:504` — `.ir-scene-scan-ring { fill: none; stroke: rgba(0, 240, 253, 0.24); stroke-width: 1; transform-origin: 1160px 390px; animation: ir-scene-scan 10s var(--xc-ease-out) infinite; }`
- `src\views\home\components\WelcomeScene.vue:505` — `.ir-scene-plate { fill: rgba(5, 17, 31, 0.82); stroke: rgba(66, 166, 195, 0.20); stroke-width: 1; }`
- `src\views\home\components\WelcomeScene.vue:506` — `.ir-scene-plate-inset { fill: rgba(8, 24, 39, 0.68); stroke: rgba(212, 225, 244, 0.08); stroke-width: 1; }`
- `src\views\home\components\WelcomeScene.vue:511` — `.ir-scene-ring-inner { fill: none; stroke: rgba(122, 224, 255, 0.28); stroke-width: 0.9; stroke-dasharray: 22 8 12 14 28 16; }`
- `src\views\home\components\WelcomeScene.vue:512` — `.ir-scene-ring-edge { fill: none; stroke: rgba(212, 225, 244, 0.14); stroke-width: 0.8; stroke-dasharray: 31 10 17 18 8 16; }`
- `src\views\home\components\WelcomeScene.vue:514` — `.ir-scene-ticks path { fill: none; stroke: rgba(122, 224, 255, 0.38); stroke-width: 1; }`
- `src\views\home\components\WelcomeScene.vue:515` — `.ir-scene-orbit ellipse { fill: none; stroke: rgba(85, 187, 216, 0.26); stroke-width: 1; stroke-dasharray: 4 7 28 12; }`
- `src\views\home\components\WelcomeScene.vue:516` — `.ir-scene-orbit rect { fill: rgba(0, 240, 253, 0.48); stroke: rgba(122, 224, 255, 0.54); stroke-width: 0.8; }`
- `src\views\home\components\WelcomeScene.vue:517` — `.ir-scene-packet-diamond { fill: rgba(154, 100, 255, 0.52); stroke: rgba(183, 155, 255, 0.65); stroke-width: 0.8; }`
- `src\views\home\components\WelcomeScene.vue:521` — `.ir-scene-locator path { fill: none; stroke: rgba(122, 224, 255, 0.52); stroke-width: 1; }`

### src\views\index-map\components\ProvinceIndexDetail.vue（24 行）

- `src\views\index-map\components\ProvinceIndexDetail.vue:83` — `.province-detail { display: grid; align-content: start; gap: 16px; min-height: 0; height: 100%; padding: 18px; box-sizing: border-box; border: 1px solid rgba(130, 154, 166, 0.2); border-radius: 8px; background: #222a2e; ...`
- `src\views\index-map\components\ProvinceIndexDetail.vue:89` — `.province-detail__identity > div span { padding: 3px 6px; border: 1px solid rgba(79, 216, 226, 0.28); border-radius: 3px; background: rgba(79, 216, 226, 0.08); color: #79dbe3; font-size: 10px; line-height: 1; white-space...`
- `src\views\index-map\components\ProvinceIndexDetail.vue:94` — `h3 > span::before { width: 3px; height: 13px; background: linear-gradient(#4fd8e2, #8067ff); content: ''; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:97` — `.province-detail__grade-ring { display: grid; width: 72px; height: 72px; flex: 0 0 auto; place-items: center; border-radius: 50%; background: conic-gradient(from -90deg, #56d9e4 0%, #8167ff var(--grade-progress), rgba(25...`
- `src\views\index-map\components\ProvinceIndexDetail.vue:98` — `.province-detail__grade-ring > div { display: grid; width: 60px; height: 60px; place-content: center; justify-items: center; border-radius: 50%; background: #222a2e; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:99` — `.province-detail__grade-ring strong { color: #f1f6f7; font-size: 24px; line-height: 1; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:100` — `.province-detail__grade-ring span { margin-top: 4px; color: #8da0a7; font-size: 9px; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:101` — `.province-detail__score { container-type: inline-size; display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; gap: 8px; min-height: 64px; padding: 13px 14px; border: 1px solid rgba(79, 216, 226, ...`
- `src\views\index-map\components\ProvinceIndexDetail.vue:103` — `.province-detail__score-value strong { color: #f3f7f8; font-size: 34px; line-height: 1; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:104` — `.province-detail__score-value span { margin-left: 4px; color: #71868e; font-size: 10px; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:105` — `.province-detail__score-advice { min-width: 0; justify-self: end; color: #f3c66f; font-size: clamp(11px, 3.5cqi, 13px); font-weight: 600; line-height: 1.45; text-align: right; text-shadow: 0 0 12px rgba(244, 180, 75, 0.1...`
- `src\views\index-map\components\ProvinceIndexDetail.vue:107` — `section + section { padding-top: 15px; border-top: 1px solid rgba(130, 154, 166, 0.14); }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:108` — `h3 b { color: #dce5e7; font-size: 11px; font-weight: 500; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:111` — `.province-detail__grid article { display: grid; gap: 8px; padding: 8px 9px; border: 1px solid rgba(130, 154, 166, 0.15); border-radius: 6px; background: rgba(255, 255, 255, 0.018); }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:113` — `.province-detail__grid span { overflow: hidden; color: #8fa0a6; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:114` — `.province-detail__grid strong { color: #dfe8ea; font-size: 14px; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:115` — `.province-detail__grid i { height: 2px; background: rgba(255, 255, 255, 0.07); overflow: hidden; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:116` — `.province-detail__grid i b { display: block; height: 100%; background: linear-gradient(90deg, #4fd8e2, #8067ff); }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:118` — `.province-detail__bar i { height: 4px; background: rgba(255, 255, 255, 0.07); overflow: hidden; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:119` — `.province-detail__bar i b { display: block; height: 100%; background: #56ced8; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:121` — `.province-detail__capacity { --capacity-color: #54c6d6; display: grid; grid-template-columns: 8px minmax(0, 1fr) auto; align-items: stretch; gap: 10px; min-height: 46px; padding: 8px 9px; box-sizing: border-box; border: ...`
- `src\views\index-map\components\ProvinceIndexDetail.vue:122` — `.province-detail__capacity--thermal { --capacity-color: #f3a64a; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:123` — `.province-detail__capacity--storage { --capacity-color: #8b5cf6; }`
- `src\views\index-map\components\ProvinceIndexDetail.vue:134` — `.province-detail__analysis { padding: 10px 11px; border: 1px solid rgba(130, 154, 166, 0.15); border-radius: 6px; background: rgba(84, 198, 214, 0.055); line-height: 1.6; }`

### src\components\TrialQuotaBadge.vue（11 行）

- `src\components\TrialQuotaBadge.vue:92` — `    linear-gradient(135deg, rgba(34, 177, 253, 0.08) 0%, rgba(110, 42, 255, 0.05) 100%),`
- `src\components\TrialQuotaBadge.vue:119` — `  box-shadow: 0 0 6px rgba(0, 240, 253, 0.55);`
- `src\components\TrialQuotaBadge.vue:150` — `  background: rgba(255, 255, 255, 0.08);`
- `src\components\TrialQuotaBadge.vue:163` — `  border-color: rgba(255, 170, 0, 0.35);`
- `src\components\TrialQuotaBadge.vue:165` — `    linear-gradient(135deg, rgba(255, 170, 0, 0.10), rgba(255, 170, 0, 0.04)),`
- `src\components\TrialQuotaBadge.vue:196` — `  border-color: rgba(34, 177, 253, 0.35);`
- `src\components\TrialQuotaBadge.vue:205` — `  box-shadow: 0 0 10px rgba(0, 240, 253, 0.6), 0 0 2px rgba(0, 240, 253, 0.9);`
- `src\components\TrialQuotaBadge.vue:212` — `  background: rgba(255, 255, 255, 0.08);`
- `src\components\TrialQuotaBadge.vue:225` — `  border-color: rgba(255, 170, 0, 0.35);`
- `src\components\TrialQuotaBadge.vue:227` — `    linear-gradient(135deg, rgba(255, 170, 0, 0.10), rgba(255, 170, 0, 0.04)),`
- `src\components\TrialQuotaBadge.vue:233` — `  box-shadow: 0 0 10px rgba(255, 170, 0, 0.55);`

### src\views\home\components\ResultCard.vue（7 行）

- `src\views\home\components\ResultCard.vue:358` — `  /* 底层不再用灰色毛玻璃，改用贴近横幅底部（采样 #000516）的深蓝黑，`
- `src\views\home\components\ResultCard.vue:360` — `  background: linear-gradient(180deg, rgba(3, 8, 22, 0.97) 0%, rgba(8, 14, 30, 0.97) 100%);`
- `src\views\home\components\ResultCard.vue:375` — `  background-color: #010515;`
- `src\views\home\components\ResultCard.vue:396` — `    linear-gradient(90deg, rgba(3, 8, 22, 0.9) 0%, rgba(3, 8, 22, 0.58) 44%, rgba(3, 8, 22, 0.14) 82%),`
- `src\views\home\components\ResultCard.vue:397` — `    linear-gradient(180deg, rgba(3, 8, 22, 0.12), rgba(3, 8, 22, 0.46));`
- `src\views\home\components\ResultCard.vue:421` — `  background: rgba(3, 8, 22, 0.54);`
- `src\views\home\components\ResultCard.vue:589` — `    background: linear-gradient(180deg, rgba(3, 8, 22, 0.18) 0%, rgba(3, 8, 22, 0.14) 34%, rgba(3, 8, 22, 0.94) 100%);`

### src\views\tie-line\components\TieLineFilterBar.vue（6 行）

- `src\views\tie-line\components\TieLineFilterBar.vue:245` — `  --tl-filter-bg: rgba(255, 255, 255, 0.035);`
- `src\views\tie-line\components\TieLineFilterBar.vue:246` — `  --tl-filter-bg-hover: rgba(255, 255, 255, 0.065);`
- `src\views\tie-line\components\TieLineFilterBar.vue:281` — `  border: 1px solid rgba(255, 255, 255, 0.075);`
- `src\views\tie-line\components\TieLineFilterBar.vue:378` — `  border-color: rgba(232, 206, 139, 0.24);`
- `src\views\tie-line\components\TieLineFilterBar.vue:379` — `  background: rgba(232, 206, 139, 0.055);`
- `src\views\tie-line\components\TieLineFilterBar.vue:403` — `  color: rgba(232, 206, 139, 0.72);`

### src\views\tie-line\components\TieLineDetailPanel.vue（5 行）

- `src\views\tie-line\components\TieLineDetailPanel.vue:114` — `.tl-profile__eyebrow { display:block; color:rgba(232, 206, 139, 0.76); font-size:12px; }`
- `src\views\tie-line\components\TieLineDetailPanel.vue:117` — `.tl-mini-route { display:grid; grid-template-columns:minmax(0, 1fr) 52px minmax(0, 1fr); align-items:start; gap:var(--xc-space-2); margin-top:var(--xc-space-5); padding:var(--xc-space-3) 0 var(--xc-space-4); border-top:1...`
- `src\views\tie-line\components\TieLineDetailPanel.vue:121` — `.tl-mini-route__dot { width:9px; height:9px; margin-top:0.35em; border-radius:999px; background:var(--tl-accent); box-shadow:0 0 0 3px rgba(6, 10, 22, 0.52), 0 0 18px var(--tl-accent); }`
- `src\views\tie-line\components\TieLineDetailPanel.vue:126` — `.tl-metric-strip__item { min-width:0; padding:var(--xc-space-3) 0; background:transparent; border-top:1px solid rgba(255, 255, 255, 0.08); }`
- `src\views\tie-line\components\TieLineDetailPanel.vue:130` — `.tl-data-basis { margin-top:var(--xc-space-4); padding-top:var(--xc-space-3); border-top:1px solid rgba(255, 255, 255, 0.08); }`

### src\views\tie-line\components\MapToolbar.vue（5 行）

- `src\views\tie-line\components\MapToolbar.vue:55` — `  border: 1px solid rgba(9, 24, 43, 0.16);`
- `src\views\tie-line\components\MapToolbar.vue:57` — `  background: rgba(245, 239, 220, 0.88);`
- `src\views\tie-line\components\MapToolbar.vue:58` — `  box-shadow: 0 8px 22px rgba(9, 24, 43, 0.22);`
- `src\views\tie-line\components\MapToolbar.vue:65` — `  background: rgba(255, 247, 223, 0.94);`
- `src\views\tie-line\components\MapToolbar.vue:66` — `  border-color: rgba(9, 24, 43, 0.24);`

### src\views\policy-market\components\ConsultationResult.vue（5 行）

- `src\views\policy-market\components\ConsultationResult.vue:377` — `.pm-result__answer-panel { padding: 18px 18px 16px; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); background: var(--xc-surface-raised); box-shadow: 0 10px 24px rgb(0 0 0 / 8%); }`
- `src\views\policy-market\components\ConsultationResult.vue:387` — `.pm-result__markdown code { border: 1px solid var(--xc-border-soft); border-radius: 4px; padding: 1px 5px; background: rgb(255 255 255 / 6%); color: var(--pm-accent, var(--xc-accent-blue)); font-family: var(--xc-font-mon...`
- `src\views\policy-market\components\ConsultationResult.vue:396` — `.pm-result__quote { border-left: 3px solid var(--pm-accent, var(--xc-accent-blue)); padding: 10px 14px; background: rgb(255 255 255 / 5%); color: var(--xc-text-soft); }`
- `src\views\policy-market\components\ConsultationResult.vue:397` — `.pm-result__code { max-width: 100%; overflow: auto; border: 1px solid var(--xc-border-soft); border-radius: var(--xc-radius-sm); padding: 12px; background: rgb(0 0 0 / 18%); color: var(--xc-text-soft); font-size: var(--x...`
- `src\views\policy-market\components\ConsultationResult.vue:402` — `.pm-result__table th { background: rgb(255 255 255 / 6%); color: var(--xc-text-strong); font-weight: var(--xc-fw-semi); }`

### src\components\ReadonlyResultCard.vue（4 行）

- `src\components\ReadonlyResultCard.vue:122` — `  background: linear-gradient(180deg, rgba(3, 8, 22, 0.97) 0%, rgba(8, 14, 30, 0.97) 100%);`
- `src\components\ReadonlyResultCard.vue:132` — `  color: rgba(219, 235, 255, 0.075);`
- `src\components\ReadonlyResultCard.vue:144` — `  background-color: #010515;`
- `src\components\ReadonlyResultCard.vue:174` — `  background: linear-gradient(90deg, rgba(3, 8, 22, 0.85) 0%, rgba(3, 8, 22, 0.45) 42%, rgba(3, 8, 22, 0) 68%);`

### src\views\policy-market\components\MarketPulse.vue（4 行）

- `src\views\policy-market\components\MarketPulse.vue:252` — `.pm-date-range-popper .el-date-table td.in-range .el-date-table-cell { background: rgba(84, 198, 214, .14) !important; }`
- `src\views\policy-market\components\MarketPulse.vue:253` — `.pm-date-range-popper .el-date-table td.start-date .el-date-table-cell, .pm-date-range-popper .el-date-table td.end-date .el-date-table-cell { background: var(--pm-accent, var(--xc-accent-blue)) !important; color: #10171...`
- `src\views\policy-market\components\MarketPulse.vue:256` — `.pm-date-range-popper .el-date-table td.start-date.today .el-date-table-cell__text, .pm-date-range-popper .el-date-table td.end-date.today .el-date-table-cell__text { color: #101719 !important; }`
- `src\views\policy-market\components\MarketPulse.vue:280` — `.pm-share-dialog__copy { border: 1px solid var(--pm-accent, var(--xc-accent-blue)); background: var(--pm-accent, var(--xc-accent-blue)); color: #101719; }`

### src\views\policy-market\index.vue（4 行）

- `src\views\policy-market\index.vue:119` — `  --pm-accent: #54c6d6;`
- `src\views\policy-market\index.vue:120` — `  --pm-surface: #283034;`
- `src\views\policy-market\index.vue:121` — `  --pm-elevated: #323b3f;`
- `src\views\policy-market\index.vue:122` — `  --pm-border: #485458;`

### src\views\tie-line\components\ChinaTieLineMap.vue（4 行）

- `src\views\tie-line\components\ChinaTieLineMap.vue:242` — `.china-tie-line-map__signature { position: absolute; left: var(--xc-space-4); top: var(--xc-space-4); z-index: 2; display: grid; gap: 2px; color: rgba(232, 206, 139, 0.42); pointer-events: none; }`
- `src\views\tie-line\components\ChinaTieLineMap.vue:244` — `.china-tie-line-map__signature strong { color: rgba(255, 255, 255, 0.20); font-size: 22px; font-weight: 600; line-height: 1; }`
- `src\views\tie-line\components\ChinaTieLineMap.vue:248` — `.china-tie-line-map__legend-title { color: rgba(232, 206, 139, 0.70); font-size: var(--xc-fs-3xs); }`
- `src\views\tie-line\components\ChinaTieLineMap.vue:252` — `.china-tie-line-map__note { position: absolute; left: var(--xc-space-4); bottom: var(--xc-space-4); z-index: var(--xc-z-raised); max-width: 360px; padding: 0; color: rgba(255, 255, 255, 0.42); font-size: var(--xc-fs-3xs)...`

### src\views\policy-market\components\ConsultationComposer.vue（3 行）

- `src\views\policy-market\components\ConsultationComposer.vue:70` — `  box-shadow: 0 14px 32px rgb(0 0 0 / 18%);`
- `src\views\policy-market\components\ConsultationComposer.vue:90` — `  box-shadow: 0 18px 40px rgb(0 0 0 / 24%);`
- `src\views\policy-market\components\ConsultationComposer.vue:111` — `.pm-composer__tools button { min-width: 124px; min-height: 44px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; border: 1px solid var(--pm-accent, var(--xc-accent-blue)); border-radius: var...`

### src\layout\index.vue（3 行）

- `src\layout\index.vue:320` — `    linear-gradient(90deg, var(--xc-surface-workspace) 0%, rgba(10, 12, 18, 0.66) 42%, transparent 74%),`
- `src\layout\index.vue:330` — `  -webkit-mask-image: linear-gradient(90deg, transparent 0%, #000 14%), linear-gradient(180deg, transparent 0%, #000 16%);`
- `src\layout\index.vue:332` — `  mask-image: linear-gradient(90deg, transparent 0%, #000 14%), linear-gradient(180deg, transparent 0%, #000 16%);`

### src\views\tie-line\components\TieLinePowerTrend.vue（3 行）

- `src\views\tie-line\components\TieLinePowerTrend.vue:182` — `.tl-power-trend { margin-top: var(--xc-space-4); padding-top: var(--xc-space-3); border-top: 1px solid rgba(255, 255, 255, 0.08); }`
- `src\views\tie-line\components\TieLinePowerTrend.vue:187` — `.tl-power-trend__range { min-width: 0; padding: var(--xc-space-1); color: var(--xc-text-mute); background: rgba(255, 255, 255, 0.035); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: var(--xc-radius-xs); font...`
- `src\views\tie-line\components\TieLinePowerTrend.vue:188` — `.tl-power-trend__range--active { color: var(--xc-text-strong); border-color: rgba(232, 206, 139, 0.38); background: rgba(232, 206, 139, 0.09); }`

### src\views\tie-line\components\tieLineMapOption.js（3 行）

- `src\views\tie-line\components\tieLineMapOption.js:164` — `      color: 'rgba(0,0,0,0)',`
- `src\views\tie-line\components\tieLineMapOption.js:174` — `        color: 'rgba(0,0,0,0)',`
- `src\views\tie-line\components\tieLineMapOption.js:235` — `      color: '#ffffff',`

### src\views\index-map\components\ChinaIndexMap.vue（2 行）

- `src\views\index-map\components\ChinaIndexMap.vue:90` — `.china-index-map__legend { position: absolute; z-index: 3; left: 12px; bottom: 12px; display: flex; flex-wrap: wrap; gap: 7px 12px; max-width: calc(100% - 24px); padding: 8px 10px; box-sizing: border-box; border: 1px sol...`
- `src\views\index-map\components\ChinaIndexMap.vue:92` — `.china-index-map__legend i { width: 9px; height: 9px; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 2px; }`

### src\views\index-map\components\IndexMapToolbar.vue（2 行）

- `src\views\index-map\components\IndexMapToolbar.vue:18` — `.index-map-tools .xc-btn { display: inline-grid; width: 44px; height: 44px; place-items: center; padding: 0; border: 1px solid var(--xc-border-soft); border-radius: 4px; background: #283034; color: var(--xc-text-soft); t...`
- `src\views\index-map\components\IndexMapToolbar.vue:19` — `.index-map-tools .xc-btn:hover { border-color: var(--xc-accent-blue); background: #323b3f; color: var(--xc-text-strong); }`

### src\views\index-map\components\IndexRankingList.vue（2 行）

- `src\views\index-map\components\IndexRankingList.vue:18` — `button { position: relative; display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; align-items: center; gap: 7px; min-width: 0; min-height: 28px; padding: 3px 6px; border: 0; border-top: 1px solid rgba(255, 255...`
- `src\views\index-map\components\IndexRankingList.vue:20` — `button:hover, button.is-active { background: rgba(84, 198, 214, 0.09); color: var(--xc-text-strong); }`

### src\components\TrialQuotaNotice.vue（2 行）

- `src\components\TrialQuotaNotice.vue:63` — `  border: 1px solid rgba(255, 170, 0, 0.35);`
- `src\components\TrialQuotaNotice.vue:66` — `  color: #ffc966;`

### src\views\tie-line\components\TieLineStatsBar.vue（2 行）

- `src\views\tie-line\components\TieLineStatsBar.vue:35` — `.tl-stats__item + .tl-stats__item::before { content: ''; position: absolute; left: calc(var(--xc-space-3) * -1); top: 4px; bottom: 4px; width: 1px; background: rgba(232, 206, 139, 0.18); }`
- `src\views\tie-line\components\TieLineStatsBar.vue:37` — `.tl-stats__value { color: var(--xc-text-strong); font-size: var(--xc-fs-kpi-sm); font-weight: var(--xc-fw-semi); line-height: var(--xc-lh-tight); white-space: nowrap; text-shadow: 0 0 20px rgba(88, 214, 207, 0.18); }`

### src\views\home\index.vue（2 行）

- `src\views\home\index.vue:1056` — `  filter: drop-shadow(0 8px 32px rgba(110, 42, 255, 0.45));`
- `src\views\home\index.vue:1655` — `    background: rgba(10, 18, 28, 0.42);`

### src\views\tie-line\index.vue（2 行）

- `src\views\tie-line\index.vue:134` — `.tie-line-page__title { margin: var(--xc-space-1) 0 0; color: var(--xc-text-strong); font-size: clamp(24px, 1.45rem, 28px); font-weight: var(--xc-fw-semi); line-height: var(--xc-lh-snug); text-shadow: 0 10px 34px rgba(88...`
- `src\views\tie-line\index.vue:135` — `.tie-line-page__subtitle { margin: var(--xc-space-1) 0 0; color: rgba(232, 206, 139, 0.66); font-size: var(--xc-fs-xs); }`

### src\views\calculation-ledger\index.vue（2 行）

- `src\views\calculation-ledger\index.vue:545` — `.ledger-calendar__days button.is-start, .ledger-calendar__days button.is-end { border-radius: var(--xc-radius-xs); background: var(--xc-accent-blue); color: #fff; }`
- `src\views\calculation-ledger\index.vue:551` — `.ledger-button--primary { border-color: var(--xc-accent-blue); background: var(--xc-accent-blue); color: #fff; }`

### src\views\index-map\index.vue（2 行）

- `src\views\index-map\index.vue:57` — `.index-map-page__map { position: relative; min-height: 0; overflow: hidden; border: 1px solid var(--xc-border-soft); border-radius: 8px; background: rgba(20, 27, 31, 0.96); }`
- `src\views\index-map\index.vue:60` — `.index-map-page__rankings { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); border: 1px solid var(--xc-border-soft); border-radius: 8px; background: rgba(40, 48, 52, 0.72); overflow: hidden; }`

### src\views\calculation-result\index.vue（1 行）

- `src\views\calculation-result\index.vue:87` — `  background: #0a0e1a;`

### src\styles\report-print.css（1 行）

- `src\styles\report-print.css:41` — `  color: rgba(219, 235, 255, 0.07);`

### src\views\home\components\RevenueDonut.vue（1 行）

- `src\views\home\components\RevenueDonut.vue:64` — `        itemStyle: { borderColor: 'rgba(36, 36, 36, 0.9)', borderWidth: 2 },`

### src\views\index-map\components\IndexPeriodSelect.vue（1 行）

- `src\views\index-map\components\IndexPeriodSelect.vue:12` — `.index-period-select :deep(.el-select__wrapper) { min-height: 36px; border: 1px solid var(--xc-border-soft); border-radius: 4px; background: #283034; box-shadow: none; }`

### src\views\index-map\components\IndexSummaryCards.vue（1 行）

- `src\views\index-map\components\IndexSummaryCards.vue:14` — `.index-summary-cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); min-height: 64px; border: 1px solid var(--xc-border-soft); border-radius: 8px; background: rgba(40, 48, 52, 0.72); overflow: hidden;...`

### src\views\public\calculation-share.vue（1 行）

- `src\views\public\calculation-share.vue:90` — `  background: #0a0e1a;`

### src\views\home\components\ShareDialog.vue（1 行）

- `src\views\home\components\ShareDialog.vue:332` — `  --el-radio-button-checked-text-color: #fff;`
