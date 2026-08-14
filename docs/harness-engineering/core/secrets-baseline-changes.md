# secrets baseline 受控更新记录

> 每次 `.secrets.baseline` 更新必须按受控流程登记：候选副本生成 → diff/哈希校验 → 人工批准 → 本文件登记 → `git add`。
> 未登记即变更 baseline 会被 `scripts/verify_secrets_baseline.py` 阻断（校验 index 相对 HEAD 变更与记录匹配）。
>
> 记录块格式（每个更新一条）：
> ```text
> ## [YYYY-MM-DD] - secrets baseline 受控更新
> - old_sha256: <变更前 baseline 的 SHA-256>
> - new_sha256: <变更后 baseline 的 SHA-256>
> - command: <生成候选副本的确切命令>
> - version: detect-secrets <版本>
> - trace_id: <关联 trace>
> - approved_by: <批准人，须为项目负责人>
> ```

<!-- 无历史受控更新记录 -->
