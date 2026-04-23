# HitX 多 Agent 协作流程验证 - TODOS

## 第一步：补测试框架 ✅

- [x] 在 workspace 初始化 pytest（.venv + pytest）
- [x] 创建 `pytest.ini` 配置
- [x] 创建 `conftest.py` 测试 fixtures
  - 临时测试数据库（从运行库复制）
  - monkeypatch database.DB_FILE
  - Flask test client fixture
- [x] 创建 `tests/test_stats.py`
  - test_stats_returns_200
  - test_stats_returns_json
  - test_stats_has_required_keys
  - test_stats_values_are_integers
  - test_stats_values_non_negative
  - test_stats_no_auth_required
- [x] 修复 bug: `/api/stats` 加入 PUBLIC_ROUTES
- [x] 测试通过（6/6）

## 第二步：走完整流程 ✅

- [x] 写代码（conftest.py + test_stats.py + pytest.ini + config.py fix）
- [x] 跑测试（pytest 6 passed）
- [x] 集成验证（curl /api/stats → 200 OK）

## 第三步：提交成果 ✅

- [x] git commit (workspace master aa255e2)
- [x] 同步到 /tmp/hitx/
- [x] 重启服务 → 200 OK
- [x] 服务正常验证

## 下一步（待办）

- [ ] 测试其他 API 端点
- [ ] CI/CD 集成
- [ ] 多模块测试覆盖
