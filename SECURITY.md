# Security Policy / 安全策略

## Reporting a vulnerability / 报告漏洞

**Do not open a public issue.** Use **Security → Report a vulnerability** on this repository; the report stays
private between you and the maintainer. If private reporting is unavailable, use the contact links on
[vertciti.com](https://vertciti.com).

**不要开公开 issue。** 请在本仓库 Security 页点 "Report a vulnerability" 私密报告；不可用时走 vertciti.com 上的联系方式。

First response within 48 hours; no substantive response within 6 business days escalates to the founder.
This mirrors the organisation policy in [HUIIIM/.github](https://github.com/HUIIIM/.github/blob/main/SECURITY.md).

## What counts as a vulnerability here / 本仓库的漏洞包括

- **A false pass.** Any input that makes a machine gate report `pass` on a page that has the defect the gate
  checks for (for example a broken reference G15 misses, or an error that is recorded as `waived`). A QA gate
  that passes a defect is this product's security bug. Please include the smallest page that reproduces it.
- **Ledger tampering that `tools/ledger-verify.py` does not detect.**
- **Command execution** through gate arguments, page content or file names.
- 门禁假 PASS、台账被改而校验不报、通过参数/页面内容/文件名执行命令，都按漏洞处理。

## Trust boundaries / 信任边界

- `QA_GATES_SECURITY_GATE`, `QA_GATES_SIZE_GATE` and `QA_GATES_CONFIG` are **trusted configuration**: the two
  gate variables name scripts that the runner executes with `bash`. Whoever can set them can run code on the
  machine. Do not let untrusted pull requests set them in CI.
- Pages under test are **untrusted data**. The runner never passes page content to a shell, and the skill
  treats instructions inside pages as content, not as instructions (`evals/injection-01.md`).
- The browser gates load the site under test in headless Chromium from a local server bound to 127.0.0.1.
  Scripts on the page run in that browser. Do not point the runner at a site you would not open yourself.
