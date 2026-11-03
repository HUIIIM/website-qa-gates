# Third-party notices / 第三方声明

The MIT licence in [LICENSE](LICENSE) covers the code and documents written for this repository. It does **not**
cover the files below, which keep their own terms.

本仓库根目录的 MIT 许可只覆盖为本仓库编写的代码与文档，**不覆盖**下列文件；它们各自适用原有条款。

| Path | What it is | Terms |
|---|---|---|
| `demo/www/dna.css` | vertciti DNA stylesheet, vendored unmodified from [HUIIIM/.github `design/dist/dna.css`](https://github.com/HUIIIM/.github/tree/main/design/dist). CI checks it has not drifted (`dna` job). | Proprietary to VERTCITY LLC, all rights reserved. Repositories owned by VERTCITY LLC may vendor it unmodified; no licence is granted to copy, modify, distribute or use it elsewhere. Full text: [HUIIIM/.github `design/LICENSE`](https://github.com/HUIIIM/.github/blob/main/design/LICENSE). |
| `demo/www/fonts/*.woff2` | Nunito Sans, Copyright 2016 The Nunito Sans Project Authors | SIL Open Font License 1.1 — [demo/www/fonts/OFL.txt](demo/www/fonts/OFL.txt) |
| `tools/browser/node_modules/` (installed by `npm ci`, not committed) | Playwright (Microsoft), axe-core (Deque Systems) | Apache-2.0 and MPL-2.0 respectively; versions and integrity hashes are locked in `tools/browser/package-lock.json` |

If you reuse this repository outside VERTCITY LLC, replace `demo/www/dna.css` with your own stylesheet.

在 VERTCITY LLC 以外复用本仓库时，请把 `demo/www/dna.css` 换成你自己的样式表。
