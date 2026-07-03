# Archived Templates

本目錄收納已歸檔（archived）的 subagent prompt templates。歸檔為 revivable，非刪除。

## 歸檔原因

`adr` / `debug` / `rtm` / `srs` 四個範本由 TASK-1050（2026-05-06）之 template 體系擴充建立，但本 repo 之任務組成（以 workflow / governance 為主）自建立後約 2 個月零 dispatch（`real_dispatch_count=0`；path-ref 僅來自建立任務 TASK-1050 自身）。為降低 `discover_templates.py` 掃描結果之雜訊而歸檔。

## 取回方式

`discover_templates.py` 以單層 glob `docs/templates/*/TEMPLATE.md` 掃描；歸檔於 `archive/<name>/`（兩層深）故不再被掃到。若日後需重新啟用某範本：`git mv docs/templates/archive/<name> docs/templates/<name>`（root 與 `template/` 鏡像同動）移回原位，並在 `docs/subagent_task_templates.md` 索引恢復對應條目。

## 來源

原建立任務：TASK-1050（subagent template 體系擴充，2026-05-06）。
