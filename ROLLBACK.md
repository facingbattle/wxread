# 上游同步回档说明

本文件记录 2026-08-11 同步上游 `findmover/wxread` 的备份点与回档方法。

## 关键提交

| 名称 | 短 hash | 完整 hash | 说明 |
| --- | --- | --- | --- |
| 合并前状态 | `f75a96c` | `f75a96c0c29f2e4e7c714e7ea2ca295219c2d324` | 备份点，等于当时的 `origin/main` |
| 合并提交 | `48fe172` | `48fe1727997869d407b2755b1de9d86eb3c522bf` | 本次上游同步产生的 merge commit |
| 上游快照 | `4e8400e` | `4e8400e436943fec4fd5bbb9a1c75581297d41c5` | 合并时的 `upstream/main` |

## 备份点

合并前状态被两个引用固定，二者指向同一提交 `f75a96c`：

- 分支 `backup/pre-upstream-merge`
- 标签 `backup-20260811`

**只要这两个引用还存在，合并前的完整历史与文件内容都不会丢失。**

## Remote 配置

| Remote | URL |
| --- | --- |
| `origin` | `https://github.com/facingbattle/wxread.git` |
| `upstream` | `https://github.com/findmover/wxread.git` |
| `gitea` | `git@gitea.zsxl.heiyu.space:zsxl/weixindushu.git` |

`upstream` 是本次新增的，用于后续直接在本地同步上游。

## 回档方法

### 方法一：整体回退到合并前（推荐）

丢弃合并提交，把 `main` 完全还原到 `f75a96c`。

```sh
git reset --hard backup/pre-upstream-merge
```

执行前若工作区有未提交改动，`--hard` 会一并丢弃。可先暂存：

```sh
git stash
git reset --hard backup/pre-upstream-merge
```

### 方法二：只还原个别文件

保留合并结果，仅把某几个文件恢复成合并前的版本。

```sh
git checkout backup/pre-upstream-merge -- main.py push.py config.py
```

例如只想恢复合并前的 `deploy.yml`：

```sh
git checkout backup/pre-upstream-merge -- .github/workflows/deploy.yml
```

### 方法三：已推送后回档

若已执行 `git push origin main` 再想回档，需要强推。**会改写远程历史，确认没有他人协作再做。**

```sh
git reset --hard backup/pre-upstream-merge
git push --force-with-lease origin main
```

### 方法四：不改写历史的反向回档

生成一个新提交来抵消合并，历史更安全。

```sh
git revert -m 1 48fe172
```

## 差异查看

回档前可先确认合并到底改了什么。

```sh
# 文件级摘要
git diff --stat backup/pre-upstream-merge main

# 某个文件的具体差异
git diff backup/pre-upstream-merge main -- main.py
```

## 本次合并的处理决策

| 文件 | 决策 |
| --- | --- |
| `config.py` `main.py` `push.py` | 采用上游版本，获得 wr_skey 修复、密钥脱敏、推送标题优化、ServerChan 支持；本地中文注释被移除 |
| `log_utils.py` | 上游新增文件 |
| `.github/workflows/deploy.yml` | 采用上游版本，其 `keepalive-job` 取代原本地 `Update run log` step |
| `Dockerfile` `README.md` `.idea/inspectionProfiles/Project_Default.xml` | Git 自动合并 |
| `.idea/.gitignore` `.idea/misc.xml` `.idea/vcs.xml` `.idea/wxread.iml` | 保留本地版本 |
| `WARP.md` `技术解析.md` `nodejs 重写可行性分析.md` `.cunzhi-memory/` `.vscode/` | 未受影响 |

## 推送前待办

- 本地运行 `python main.py` 验证功能是否正常
- 若使用 ServerChan 推送，需在 GitHub 仓库添加 secret `SERVERCHAN_SPT`
- `keepalive-job` 需要 `actions: write` 权限，确认仓库 Actions 设置允许
- 确认无误后执行 `git push origin main`

## 备份清理

确认合并结果稳定运行一段时间后，可删除备份引用：

```sh
git branch -D backup/pre-upstream-merge
git tag -d backup-20260811
```

**在完全确认之前不要删除。**

## 后续同步上游的标准流程

```sh
git fetch upstream
git merge upstream/main
```
