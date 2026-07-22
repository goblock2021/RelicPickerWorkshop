# RelicPicker 创意工坊

Elden Ring Nightreign 遗物配置分享仓库。

由 [RelicPicker](https://github.com/goblock2021/RelicPicker) 应用驱动。

## 如何分享

1. 在 RelicPicker 应用中打开**创意工坊**
2. 配置 GitHub Token（需要 `public_repo` 权限）
3. 点击分享按钮，填写标题和描述
4. 应用会自动创建 Pull Request
5. GitHub Actions 会自动审核并合并

## 如何删除

在应用中点击你自己的配置旁边的删除按钮即可自动提交删除 PR。

## 数据格式

每个分享存储在 `submissions/` 目录下，格式为 JSON：

```json
{
  "id": "uuid",
  "author": "github-username",
  "title": "配置名称",
  "description": "配置描述",
  "effects": [{"eff_id": 7010900, "curse_id": null}],
  "shop": "normal-new",
  "color": 0,
  "relic_id": 200,
  "effect_names": ["效果名"],
  "curse_names": [],
  "relic_name": "遗物名",
  "created_at": "2026-07-22T12:00:00Z"
}
```

## 自动化

所有 PR 由 GitHub Actions 自动审核：
- JSON 格式和字段验证
- 重复检查（相同效果+商店+颜色+遗物）
- 删除授权检查（仅作者可删除自己的分享）

🤖 Generated with [Claude Code](https://claude.com/claude-code)
