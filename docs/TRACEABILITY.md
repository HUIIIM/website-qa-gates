# 门禁 ↔ 测试追溯矩阵 / Gate-to-test traceability

由 `tools/trace-matrix.py --write` 从 `tests/` 的 `[门禁:方向]` 标注生成，CI 用 `--check` 校验，请勿手改。
Generated from the `[gate:direction]` tags in `tests/`; CI checks it with `--check`. Do not edit by hand.

| 门禁 | 名称 / Name | pass 用例 | fail 用例 | waived 用例 | 状态 |
|---|---|---|---|---|---|
| G1 | data-room 敏感扫描 / sensitive-content scan | `TestCleanDemo.test_demo_passes_every_static_gate`<br>`TestScriptGates.test_external_script_receives_site_root`<br>`TestScriptGates.test_site_specific_secret_pattern_comes_from_config`<br>`TestSecretScan.test_allowlist_excludes_line_and_is_not_scanned_itself`<br>`TestSecretScan.test_binary_files_skipped`<br>`TestSecretScan.test_lowercase_secret_word_is_not_a_hit` | `TestPathsWithSpaces.test_g1_secret_in_spaced_root`<br>`TestScriptGates.test_missing_external_script_is_fail`<br>`TestScriptGates.test_nonzero_exit_without_fail_text_is_fail`<br>`TestScriptGates.test_site_specific_secret_pattern_comes_from_config`<br>`TestScriptGates.test_timeout_is_fail`<br>`TestSecretScan.test_bad_extra_pattern_is_usage_error`<br>`TestSecretScan.test_classification_marking_is_a_hit`<br>`TestSecretScan.test_more_token_shapes`<br>`TestSecretScan.test_tokens_in_unlisted_extensions` | — | ✓ |
| G4 | 体积预算 / size budget | `TestCleanDemo.test_demo_passes_every_static_gate`<br>`TestScriptGates.test_external_script_receives_site_root` | `TestScriptGates.test_nonzero_exit_without_fail_text_is_fail`<br>`TestSizeBudget.test_page_total_over_budget`<br>`TestSizeBudget.test_required_page_missing`<br>`TestSizeBudget.test_single_file_over_budget` | — | ✓ |
| G5 | 中英镜像（机械项） / zh/en mirror (mechanical) | `TestCleanDemo.test_demo_passes_every_static_gate` | `TestMirror.test_fullwidth_punctuation_in_english`<br>`TestMirror.test_numbers_must_match` | `TestMirror.test_no_pairs_is_waived` | ✓ |
| G7 | CSP hash round-trip / CSP hash round-trip | `TestCsp.test_hash_round_trip`<br>`TestCsp.test_json_ld_is_not_a_script` | `TestCsp.test_hash_round_trip`<br>`TestCsp.test_inline_script_without_hash_is_fail` | `TestCsp.test_no_csp_is_waived` | ✓ |
| G8 | 生产可达性 / production reachability | `TestReachability.test_g8_reachable_local_server` | `TestReachability.test_non_http_scheme_rejected`<br>`TestReachability.test_site_url_with_shell_metacharacters` | `TestReachability.test_no_url_is_waived` | ✓ |
| G15 | 站内资源完整性 / local resource integrity | `TestCleanDemo.test_demo_passes_every_static_gate`<br>`TestLocalResources.test_script_and_comment_text_ignored`<br>`TestLocalResources.test_valid_refs` | `TestLocalResources.test_css_file_urls`<br>`TestLocalResources.test_dead_links`<br>`TestLocalResources.test_missing_image`<br>`TestLocalResources.test_refs_the_old_gate_missed` | — | ✓ |
| A1 | 字阶命中 / type scale | `TestCleanDemo.test_demo_passes_every_static_gate` | `TestPathsWithSpaces.test_a1_font_size` | — | ✓ |
| A2 | 8pt 间距 / 8pt spacing | `TestCleanDemo.test_demo_passes_every_static_gate`<br>`TestDesignRules.test_vendored_dna_is_excluded_and_disclosed`<br>`TestPathsWithSpaces.test_a2_does_not_read_across_tags` | `TestDesignRules.test_vendored_dna_is_excluded_and_disclosed`<br>`TestPathsWithSpaces.test_a2_spacing` | — | ✓ |
| A5 | count-up 归零 / no count-up | `TestCleanDemo.test_demo_passes_every_static_gate` | `TestDesignRules.test_count_up_in_script` | — | ✓ |
| T1 | eyebrow 计数 / eyebrow count | `TestCleanDemo.test_demo_passes_every_static_gate`<br>`TestDesignRules.test_eyebrow_ratio` | `TestDesignRules.test_eyebrow_ratio` | — | ✓ |
| T2 | em-dash 零 / no em-dash | `TestCleanDemo.test_demo_passes_every_static_gate`<br>`TestDesignRules.test_em_dash` | `TestDesignRules.test_em_dash` | — | ✓ |
| G12-1 | 动效白名单属性 / motion property whitelist | `TestCleanDemo.test_demo_passes_every_static_gate`<br>`TestDesignRules.test_keyframes`<br>`TestDesignRules.test_whitelisted_transitions_pass` | `TestDesignRules.test_keyframes`<br>`TestDesignRules.test_mixed_transition_is_fail`<br>`TestDesignRules.test_transition_all_and_implicit_all`<br>`TestDesignRules.test_vendored_dna_is_excluded_and_disclosed`<br>`TestDesignRules.test_violation_after_40_declarations` | — | ✓ |
| G12-4 | 禁粒子背景 / no particle backgrounds | `TestCleanDemo.test_demo_passes_every_static_gate` | `TestDesignRules.test_particle_library` | — | ✓ |
| G2 | 触控目标 / touch targets | `TestBrowserGates.test_clean_demo_passes` | `TestBrowserGates.test_defects_are_caught` | — | ✓ |
| G3 | 390px 零横向截断 / no horizontal overflow at 390px | `TestBrowserGates.test_clean_demo_passes` | `TestBrowserGates.test_defects_are_caught` | — | ✓ |
| G9 | 真机渲染复验 / real-browser render check | `TestBrowserGates.test_clean_demo_passes` | `TestBrowserGates.test_defects_are_caught`<br>`TestBrowserGates.test_production_csp_is_enforced` | — | ✓ |
| A4 | 键盘可达与焦点环 / keyboard reach and focus ring | `TestBrowserGates.test_clean_demo_passes` | `TestBrowserGates.test_defects_are_caught` | — | ✓ |
| M4 | 减少动态效果 / reduced motion | `TestBrowserGates.test_clean_demo_passes` | `TestBrowserGates.test_defects_are_caught` | — | ✓ |
| T5 | CTA 单行 / single-line CTA | `TestBrowserGates.test_clean_demo_passes` | `TestBrowserGates.test_defects_are_caught` | — | ✓ |
| G16 | axe WCAG 自动扫描 / axe WCAG scan | `TestBrowserGates.test_clean_demo_passes` | `TestBrowserGates.test_defects_are_caught` | — | ✓ |
| V4 | 拦截/放行记录 / interception record | `TestV4.test_disposition_record_clears_v4`<br>`TestV4.test_fail_with_output_evidence`<br>`TestV4.test_v4_fail_is_not_an_interception` | `TestV4.test_disposition_record_clears_v4`<br>`TestV4.test_fail_without_output_evidence` | — | ✓ |

## 其他受测行为 / Other tested behaviour

| 标注 | 用例 |
|---|---|
| INT-2:two-person/validation | `TestLedgerChain.test_closing_needs_a_second_person`<br>`TestLedgerChain.test_unknown_interception` |
| M1:waived | `TestBrowserGates.test_clean_demo_passes` |
| config:validation | `TestDesignRules.test_exclusion_requires_reason` |
| injection:machine | `TestPromptInjection.test_instruction_in_page_does_not_change_verdicts` |
| ledger:privacy/schema/seal/tamper | `TestLedgerChain.test_ledger_matches_schema`<br>`TestLedgerChain.test_rewriting_history_is_detected`<br>`TestLedgerChain.test_truncating_the_tail_is_detected`<br>`TestRunnerEndToEnd.test_home_dir_is_masked`<br>`TestRunnerEndToEnd.test_ledger_env_relative_paths_and_seal`<br>`TestRunnerEndToEnd.test_tampered_additive_flag_refuses_write` |
| runner:fail-closed/i18n/missing-root/no-shell | `TestFailClosed.test_broken_symlink_fails_instead_of_waiving`<br>`TestReachability.test_site_root_with_shell_metacharacters`<br>`TestRunnerEndToEnd.test_english_output`<br>`TestRunnerEndToEnd.test_missing_root_exits_2_without_writing` |
| score:filing/na/scorecard/validation | `TestScore.test_cli_requires_owner_when_filing`<br>`TestScore.test_filing_rules`<br>`TestScore.test_input_errors`<br>`TestScore.test_na_is_removed_from_the_denominator`<br>`TestScore.test_scorecard_is_parsed` |
