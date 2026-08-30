# Contributing to korux-repertoire

本仓只收 **Capability Package**（manifest + governor + docs）。运行时消费由 Korux 锁定 Release zip。

## 本地校验

阶段 1 起（脚本进仓后）：

```bash
./scripts/validate_all.sh
# 或单包：
python scripts/validate_capability_package.py packages/<id>