# website-qa-gates

**Ship websites that prove the company's caliber.** A skill that runs pre-release quality gates on website changes: per-gate pass/fail verdicts with evidence, an 11-dimension weighted score with grade, and automatic issue filing when below A-grade.

Built for [Miao](https://vertciti.com) (Jiahui Miao) — N=1 founder IP infrastructure.

## What it delivers

Three things per website change:

1. **Gate verdicts** — G1–G9 + G14 release gates + 4 motion-specific gates, each PASS / FAIL / conditional with evidence. Any FAIL blocks release.
2. **11-dimension score** — Weighted 100-point model (real-browser verification 18, visual craft 12, CTA closure 12, perf budget 12, …). Grades: S ≥95 / A++ ≥90 / A ≥85 / B ≥70 / C <70.
3. **Auto-filing** — Below A-grade (or any gate FAIL) automatically files a remediation record with owner and 24h deadline.

## Quick start

```bash
cd demo
bash run.sh
# Runs the real gate runner against a test page (~30s)
```

See `demo/README.md` for details. Machine-runnable gates execute for real; browser-dependent gates are honestly marked `waived` (never faked).

## References

- `references/gate-checklist.md` — Per-gate execution methods and pass criteria.
- `references/scorecard-v1.yaml` — Machine-readable scoring model.
- `evals/` — Smoke evaluations with real dry-run records.

## License

MIT — see [LICENSE](LICENSE).

## Author

**Jiahui Miao** — Founder, [vertciti](https://vertciti.com). Building procurement infrastructure for AI agents. Participates in 3GPP working on 6G core network standards.
