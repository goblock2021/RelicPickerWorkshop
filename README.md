# RelicPicker 创意工坊

Elden Ring Nightreign 遗物配置分享仓库。

由 [RelicPicker](https://github.com/goblock2021/RelicPicker) 应用驱动。

## 如何分享

### 通过应用（推荐）

1. 在 RelicPicker 应用中打开**创意工坊**
2. 配置 GitHub Token（需要 `public_repo` 权限）
3. 点击分享按钮，填写标题和描述
4. 应用会自动创建 Issue 提交
5. GitHub Actions 会自动审核并合并

### 手动提交

1. 在 [Issues](../../issues) 页面点击 **New Issue**
2. 标题填写你的配置名称
3. 正文第一行写 `[RELICPICKER_SHARE]`
4. 在json代码块中填入你的配置数据（参考下方[数据格式](#数据格式)）
5. 提交 Issue，GitHub Actions 会自动处理

## 如何删除

### 通过应用（推荐）

在应用中点击你自己的配置旁边的删除按钮即可自动提交删除 Issue。

### 手动提交

1. 在 [Issues](../../issues) 页面点击 **New Issue**
2. 标题填写删除请求
3. 正文第一行写 `[RELICPICKER_DELETE]`
4. 在正文中注明要删除的 `submission_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
5. 提交 Issue，GitHub Actions 会自动处理（仅作者可删除自己的分享）

## 数据格式

每个分享存储在 `submissions/` 目录下，文件名 `{uuid}.json`。

用户提交的数据经过**字段白名单过滤**，仅保留 `title`、`description`、`relics`，其余元数据由系统自动生成。

### 提交格式（用户侧）

应用提交时仅包含以下三个字段：

```json
{
  "title": "配置名称",
  "description": "配置描述",
  "relics": [
    {
      "effects": [{"eff_id": 7010900}],
      "shop": "normal-new",
      "color": 0,
      "relic_id": 200,
      "effect_names": ["效果名"],
      "curse_names": [],
      "relic_name": "遗物名"
    }
  ]
}
```

> `relics` 是数组，一次可分享多个遗物配置。`shop` 取值为 `normal-old` / `normal-new` / `deep-old` / `deep-new`。

### 存储格式（服务端自动补充）

系统审核通过后自动补充以下字段写入文件：

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "author": "github-username",
  "created_at": "2026-07-22T12:00:00Z",
  "version": 1,
  "issue_number": 42,
  "data": {
    "title": "配置名称",
    "description": "配置描述",
    "relics": [...]
  }
}
```

| 字段             | 说明                       |
| -------------- | ------------------------ |
| `id`           | UUID，系统自动生成              |
| `author`       | 取自 Issue 创建者的 GitHub 用户名 |
| `created_at`   | 创建时间（UTC）                |
| `version`      | 格式版本号                    |
| `issue_number` | 关联的 GitHub Issue 编号      |
| `data`         | 用户提交的原始数据                |

## 自动化

所有 Issue 由 GitHub Actions 自动审核（`[RELICPICKER_SHARE]` / `[RELICPICKER_DELETE]` 标记）：

- JSON 格式和字段白名单验证（拒绝伪造的 `id`、`author` 等字段）
- 字段类型和取值范围校验
- 删除授权检查（仅作者可删除自己的分享）
- 审核完成后自动关闭 Issue
