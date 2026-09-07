#!/usr/bin/env python3
"""Convert governor.json rule messages to {en, zh_CN, zh_HK} objects."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKAGES = REPO / "packages"

# Exact-string → trilingual. Fallback: copy source into all locales.
TRANSLATIONS: dict[str, dict[str, str]] = {
    "Meitu product image processing requires human approval": {
        "en": "Meitu product image processing requires human approval",
        "zh_CN": "美图商品图处理前须人工确认",
        "zh_HK": "美圖商品圖處理前須人工確認",
    },
    "product_image_file_id is empty": {
        "en": "product_image_file_id is empty",
        "zh_CN": "product_image_file_id 为空",
        "zh_HK": "product_image_file_id 為空",
    },
    "Caption contains a blocked keyword": {
        "en": "Caption contains a blocked keyword",
        "zh_CN": "文案包含禁止关键字",
        "zh_HK": "文案包含禁止關鍵字",
    },
    "CMS item name is empty": {
        "en": "CMS item name is empty",
        "zh_CN": "CMS 条目名称为空",
        "zh_HK": "CMS 條目名稱為空",
    },
    "CMS item slug is empty": {
        "en": "CMS item slug is empty",
        "zh_CN": "CMS 条目 slug 为空",
        "zh_HK": "CMS 條目 slug 為空",
    },
    "CMS item name contains a blocked keyword": {
        "en": "CMS item name contains a blocked keyword",
        "zh_CN": "CMS 条目名称包含禁止关键字",
        "zh_HK": "CMS 條目名稱包含禁止關鍵字",
    },
    "Webflow CMS create/publish requires human approval": {
        "en": "Webflow CMS create/publish requires human approval",
        "zh_CN": "Webflow CMS 创建/发布前须人工确认",
        "zh_HK": "Webflow CMS 建立/發佈前須人工確認",
    },
    "推文正文为空；须使用上游步骤产出": {
        "en": "Tweet body is empty; use upstream step output.",
        "zh_CN": "推文正文为空；须使用上游步骤产出",
        "zh_HK": "推文正文為空；須使用上游步驟產出",
    },
    "推文包含禁止关键字": {
        "en": "Tweet contains a blocked keyword",
        "zh_CN": "推文包含禁止关键字",
        "zh_HK": "推文包含禁止關鍵字",
    },
    "推文包含禁止的链接域名": {
        "en": "Tweet contains a blocked URL host",
        "zh_CN": "推文包含禁止的链接域名",
        "zh_HK": "推文包含禁止的連結域名",
    },
    "推文超过 Owner 设定的字数上限": {
        "en": "Tweet exceeds Owner max character limit",
        "zh_CN": "推文超过 Owner 设定的字数上限",
        "zh_HK": "推文超過 Owner 設定的字數上限",
    },
    "推文 @ 次数超过上限": {
        "en": "Tweet @ mention count exceeds the limit",
        "zh_CN": "推文 @ 次数超过上限",
        "zh_HK": "推文 @ 次數超過上限",
    },
    "Owner 要求发帖必须带图": {
        "en": "Owner requires posts to include an image",
        "zh_CN": "Owner 要求发帖必须带图",
        "zh_HK": "Owner 要求發帖必須帶圖",
    },
    "发布推文前须人工确认": {
        "en": "Human confirmation required before publishing a tweet",
        "zh_CN": "发布推文前须人工确认",
        "zh_HK": "發佈推文前須人工確認",
    },
    "Post title is empty": {
        "en": "Post title is empty",
        "zh_CN": "帖子标题为空",
        "zh_HK": "帖子標題為空",
    },
    "Post content is empty": {
        "en": "Post content is empty",
        "zh_CN": "帖子正文为空",
        "zh_HK": "帖子正文為空",
    },
    "Post content contains a blocked keyword": {
        "en": "Post content contains a blocked keyword",
        "zh_CN": "帖子正文包含禁止关键字",
        "zh_HK": "帖子正文包含禁止關鍵字",
    },
    "Post content contains a blocked URL host": {
        "en": "Post content contains a blocked URL host",
        "zh_CN": "帖子正文包含禁止的链接域名",
        "zh_HK": "帖子正文包含禁止的連結域名",
    },
    "Post content exceeds Owner max_chars": {
        "en": "Post content exceeds Owner max_chars",
        "zh_CN": "帖子正文超过 Owner 字数上限",
        "zh_HK": "帖子正文超過 Owner 字數上限",
    },
    "WordPress post create/publish requires human approval": {
        "en": "WordPress post create/publish requires human approval",
        "zh_CN": "WordPress 发帖/发布前须人工确认",
        "zh_HK": "WordPress 發帖/發佈前須人工確認",
    },
    "IMAP poll is External read; default gate auto": {
        "en": "IMAP poll is External read; default gate auto",
        "zh_CN": "IMAP 轮询为 External 读取；默认 gate 为 auto",
        "zh_HK": "IMAP 輪詢為 External 讀取；預設 gate 為 auto",
    },
    "邮件正文为空；须使用上游步骤产出": {
        "en": "Email body is empty; use upstream step output.",
        "zh_CN": "邮件正文为空；须使用上游步骤产出",
        "zh_HK": "郵件正文為空；須使用上游步驟產出",
    },
    "Email body matches an owner blocked keyword.": {
        "en": "Email body matches an owner blocked keyword.",
        "zh_CN": "邮件正文命中 Owner 禁止关键字。",
        "zh_HK": "郵件正文命中 Owner 禁止關鍵字。",
    },
    "Email subject matches an owner blocked keyword.": {
        "en": "Email subject matches an owner blocked keyword.",
        "zh_CN": "邮件主题命中 Owner 禁止关键字。",
        "zh_HK": "郵件主題命中 Owner 禁止關鍵字。",
    },
    "Email body shorter than owner min_body_length.": {
        "en": "Email body shorter than owner min_body_length.",
        "zh_CN": "邮件正文短于 Owner 设定的最小长度。",
        "zh_HK": "郵件正文短於 Owner 設定的最小長度。",
    },
    "发送邮件前须人工确认": {
        "en": "Human confirmation required before sending email",
        "zh_CN": "发送邮件前须人工确认",
        "zh_HK": "發送郵件前須人工確認",
    },
    "campaign_id is empty": {
        "en": "campaign_id is empty",
        "zh_CN": "campaign_id 为空",
        "zh_HK": "campaign_id 為空",
    },
    "Google Ads mutate (spend-affecting) requires human approval": {
        "en": "Google Ads mutate (spend-affecting) requires human approval",
        "zh_CN": "Google Ads 变更（影响花费）前须人工确认",
        "zh_HK": "Google Ads 變更（影響花費）前須人工確認",
    },
    "Campaign HTML contains a blocked keyword": {
        "en": "Campaign HTML contains a blocked keyword",
        "zh_CN": "活动 HTML 包含禁止关键字",
        "zh_HK": "活動 HTML 包含禁止關鍵字",
    },
    "Campaign HTML contains a blocked URL host": {
        "en": "Campaign HTML contains a blocked URL host",
        "zh_CN": "活动 HTML 包含禁止的链接域名",
        "zh_HK": "活動 HTML 包含禁止的連結域名",
    },
    "Klaviyo campaign create/send requires human approval": {
        "en": "Klaviyo campaign create/send requires human approval",
        "zh_CN": "Klaviyo 活动创建/发送前须人工确认",
        "zh_HK": "Klaviyo 活動建立/發送前須人工確認",
    },
    "Canva design export / autofill requires human approval": {
        "en": "Canva design export / autofill requires human approval",
        "zh_CN": "Canva 设计导出/自动填充前须人工确认",
        "zh_HK": "Canva 設計匯出/自動填充前須人工確認",
    },
    "交易数量超过工作区上限，须人工审批": {
        "en": "Order quantity exceeds workspace limit; human approval required",
        "zh_CN": "交易数量超过工作区上限，须人工审批",
        "zh_HK": "交易數量超過工作區上限，須人工審批",
    },
    "下单前须人工确认": {
        "en": "Human confirmation required before placing an order",
        "zh_CN": "下单前须人工确认",
        "zh_HK": "下單前須人工確認",
    },
    "object_id is empty": {
        "en": "object_id is empty",
        "zh_CN": "object_id 为空",
        "zh_HK": "object_id 為空",
    },
    "Meta ads mutate (spend-affecting) requires human approval": {
        "en": "Meta ads mutate (spend-affecting) requires human approval",
        "zh_CN": "Meta 广告变更（影响花费）前须人工确认",
        "zh_HK": "Meta 廣告變更（影響花費）前須人工確認",
    },
    "Mailchimp campaign create/send requires human approval": {
        "en": "Mailchimp campaign create/send requires human approval",
        "zh_CN": "Mailchimp 活动创建/发送前须人工确认",
        "zh_HK": "Mailchimp 活動建立/發送前須人工確認",
    },
    "Video title is empty": {
        "en": "Video title is empty",
        "zh_CN": "视频标题为空",
        "zh_HK": "影片標題為空",
    },
    "Title contains a blocked keyword": {
        "en": "Title contains a blocked keyword",
        "zh_CN": "标题包含禁止关键字",
        "zh_HK": "標題包含禁止關鍵字",
    },
    "YouTube upload requires human approval": {
        "en": "YouTube upload requires human approval",
        "zh_CN": "YouTube 上传前须人工确认",
        "zh_HK": "YouTube 上傳前須人工確認",
    },
    "Edit prompt is empty": {
        "en": "Edit prompt is empty",
        "zh_CN": "编辑提示词为空",
        "zh_HK": "編輯提示詞為空",
    },
    "Prompt contains a blocked keyword": {
        "en": "Prompt contains a blocked keyword",
        "zh_CN": "提示词包含禁止关键字",
        "zh_HK": "提示詞包含禁止關鍵字",
    },
    "Alibaba Wanxiang image edit requires human approval": {
        "en": "Alibaba Wanxiang image edit requires human approval",
        "zh_CN": "阿里万相图片编辑前须人工确认",
        "zh_HK": "阿里萬相圖片編輯前須人工確認",
    },
    "Notion 正文为空；须使用上游步骤产出": {
        "en": "Notion body is empty; use upstream step output.",
        "zh_CN": "Notion 正文为空；须使用上游步骤产出",
        "zh_HK": "Notion 正文為空；須使用上游步驟產出",
    },
    "Notion body shorter than owner min_body_length.": {
        "en": "Notion body shorter than owner min_body_length.",
        "zh_CN": "Notion 正文短于 Owner 设定的最小长度。",
        "zh_HK": "Notion 正文短於 Owner 設定的最小長度。",
    },
    "Notion title is empty.": {
        "en": "Notion title is empty.",
        "zh_CN": "Notion 标题为空。",
        "zh_HK": "Notion 標題為空。",
    },
    "写入 Notion 前须人工确认": {
        "en": "Human confirmation required before writing to Notion",
        "zh_CN": "写入 Notion 前须人工确认",
        "zh_HK": "寫入 Notion 前須人工確認",
    },
    "Company contains a blocked keyword": {
        "en": "Company contains a blocked keyword",
        "zh_CN": "公司名包含禁止关键字",
        "zh_HK": "公司名包含禁止關鍵字",
    },
    "HubSpot contact upsert requires human approval": {
        "en": "HubSpot contact upsert requires human approval",
        "zh_CN": "HubSpot 联系人写入前须人工确认",
        "zh_HK": "HubSpot 聯絡人寫入前須人工確認",
    },
    "Note body is empty": {
        "en": "Note body is empty",
        "zh_CN": "备注正文为空",
        "zh_HK": "備註正文為空",
    },
    "Note contains a blocked keyword": {
        "en": "Note contains a blocked keyword",
        "zh_CN": "备注包含禁止关键字",
        "zh_HK": "備註包含禁止關鍵字",
    },
    "Note exceeds Owner max_chars": {
        "en": "Note exceeds Owner max_chars",
        "zh_CN": "备注超过 Owner 字数上限",
        "zh_HK": "備註超過 Owner 字數上限",
    },
    "HubSpot CRM writes require human approval": {
        "en": "HubSpot CRM writes require human approval",
        "zh_CN": "HubSpot CRM 写入前须人工确认",
        "zh_HK": "HubSpot CRM 寫入前須人工確認",
    },
    "帖文为空；须使用上游步骤产出": {
        "en": "Post body is empty; use upstream step output.",
        "zh_CN": "帖文为空；须使用上游步骤产出",
        "zh_HK": "帖文為空；須使用上游步驟產出",
    },
    "帖文包含禁止关键字": {
        "en": "Post contains a blocked keyword",
        "zh_CN": "帖文包含禁止关键字",
        "zh_HK": "帖文包含禁止關鍵字",
    },
    "帖文包含禁止的链接域名": {
        "en": "Post contains a blocked URL host",
        "zh_CN": "帖文包含禁止的链接域名",
        "zh_HK": "帖文包含禁止的連結域名",
    },
    "帖文超过 Owner 设定的字数上限": {
        "en": "Post exceeds Owner max character limit",
        "zh_CN": "帖文超过 Owner 设定的字数上限",
        "zh_HK": "帖文超過 Owner 設定的字數上限",
    },
    "帖文 @ 次数超过上限": {
        "en": "Post @ mention count exceeds the limit",
        "zh_CN": "帖文 @ 次数超过上限",
        "zh_HK": "帖文 @ 次數超過上限",
    },
    "发布 Facebook Page 帖前须人工确认": {
        "en": "Human confirmation required before publishing a Facebook Page post",
        "zh_CN": "发布 Facebook Page 帖前须人工确认",
        "zh_HK": "發佈 Facebook Page 帖前須人工確認",
    },
    "Note caption is empty": {
        "en": "Note caption is empty",
        "zh_CN": "笔记文案为空",
        "zh_HK": "筆記文案為空",
    },
    "Xiaohongshu publish requires human approval": {
        "en": "Xiaohongshu publish requires human approval",
        "zh_CN": "小红书发布前须人工确认",
        "zh_HK": "小紅書發佈前須人工確認",
    },
    "Search query matches an owner blocked keyword.": {
        "en": "Search query matches an owner blocked keyword.",
        "zh_CN": "搜索关键词命中 Owner 禁止关键字。",
        "zh_HK": "搜尋關鍵詞命中 Owner 禁止關鍵字。",
    },
    "搜索关键词为空；请在上游步骤提供查询文本": {
        "en": "Search query is empty; provide query text from an upstream step.",
        "zh_CN": "搜索关键词为空；请在上游步骤提供查询文本",
        "zh_HK": "搜尋關鍵詞為空；請在上游步驟提供查詢文本",
    },
    "TikTok publish requires human approval": {
        "en": "TikTok publish requires human approval",
        "zh_CN": "TikTok 发布前须人工确认",
        "zh_HK": "TikTok 發佈前須人工確認",
    },
    "Caption is empty; use upstream step output": {
        "en": "Caption is empty; use upstream step output",
        "zh_CN": "文案为空；须使用上游步骤产出",
        "zh_HK": "文案為空；須使用上游步驟產出",
    },
    "Instagram Feed posts require image_file_id": {
        "en": "Instagram Feed posts require image_file_id",
        "zh_CN": "Instagram Feed 发帖需要 image_file_id",
        "zh_HK": "Instagram Feed 發帖需要 image_file_id",
    },
    "Caption contains a blocked URL host": {
        "en": "Caption contains a blocked URL host",
        "zh_CN": "文案包含禁止的链接域名",
        "zh_HK": "文案包含禁止的連結域名",
    },
    "Caption exceeds Owner max_chars": {
        "en": "Caption exceeds Owner max_chars",
        "zh_CN": "文案超过 Owner 字数上限",
        "zh_HK": "文案超過 Owner 字數上限",
    },
    "Caption @ mention count exceeds Owner limit": {
        "en": "Caption @ mention count exceeds Owner limit",
        "zh_CN": "文案 @ 次数超过 Owner 上限",
        "zh_HK": "文案 @ 次數超過 Owner 上限",
    },
    "Instagram Feed posts require human approval": {
        "en": "Instagram Feed posts require human approval",
        "zh_CN": "Instagram Feed 发帖前须人工确认",
        "zh_HK": "Instagram Feed 發帖前須人工確認",
    },
    "Commentary is empty; use upstream step output": {
        "en": "Commentary is empty; use upstream step output",
        "zh_CN": "评论正文为空；须使用上游步骤产出",
        "zh_HK": "評論正文為空；須使用上游步驟產出",
    },
    "Commentary contains a blocked keyword": {
        "en": "Commentary contains a blocked keyword",
        "zh_CN": "评论包含禁止关键字",
        "zh_HK": "評論包含禁止關鍵字",
    },
    "Commentary contains a blocked URL host": {
        "en": "Commentary contains a blocked URL host",
        "zh_CN": "评论包含禁止的链接域名",
        "zh_HK": "評論包含禁止的連結域名",
    },
    "Commentary exceeds Owner max_chars": {
        "en": "Commentary exceeds Owner max_chars",
        "zh_CN": "评论超过 Owner 字数上限",
        "zh_HK": "評論超過 Owner 字數上限",
    },
    "Commentary @ mention count exceeds Owner limit": {
        "en": "Commentary @ mention count exceeds Owner limit",
        "zh_CN": "评论 @ 次数超过 Owner 上限",
        "zh_HK": "評論 @ 次數超過 Owner 上限",
    },
    "Owner requires an image on LinkedIn posts": {
        "en": "Owner requires an image on LinkedIn posts",
        "zh_CN": "Owner 要求 LinkedIn 发帖必须带图",
        "zh_HK": "Owner 要求 LinkedIn 發帖必須帶圖",
    },
    "LinkedIn Company Page posts require human approval": {
        "en": "LinkedIn Company Page posts require human approval",
        "zh_CN": "LinkedIn 公司页发帖前须人工确认",
        "zh_HK": "LinkedIn 公司頁發帖前須人工確認",
    },
    # Template
    "Body is empty; use upstream step output.": {
        "en": "Body is empty; use upstream step output.",
        "zh_CN": "正文为空；须使用上游步骤产出。",
        "zh_HK": "正文為空；須使用上游步驟產出。",
    },
    "Body matches an owner blocked keyword.": {
        "en": "Body matches an owner blocked keyword.",
        "zh_CN": "正文命中 Owner 禁止关键字。",
        "zh_HK": "正文命中 Owner 禁止關鍵字。",
    },
    "Body shorter than owner min_body_length.": {
        "en": "Body shorter than owner min_body_length.",
        "zh_CN": "正文短于 Owner 设定的最小长度。",
        "zh_HK": "正文短於 Owner 設定的最小長度。",
    },
    "Human confirmation required before external write.": {
        "en": "Human confirmation required before external write.",
        "zh_CN": "写外联前须人工确认。",
        "zh_HK": "寫外聯前須人工確認。",
    },
}


def to_i18n(message: object) -> dict[str, str]:
    if isinstance(message, dict):
        en = str(message.get("en") or "").strip()
        zh_cn = str(message.get("zh_CN") or message.get("zh-CN") or "").strip()
        zh_hk = str(message.get("zh_HK") or message.get("zh-HK") or "").strip()
        base = en or zh_cn or zh_hk
        hit = TRANSLATIONS.get(base) or TRANSLATIONS.get(en) or TRANSLATIONS.get(zh_cn)
        if hit:
            return dict(hit)
        return {
            "en": en or base,
            "zh_CN": zh_cn or en or base,
            "zh_HK": zh_hk or zh_cn or en or base,
        }
    text = str(message or "").strip()
    if text in TRANSLATIONS:
        return dict(TRANSLATIONS[text])
    # Fallback: same string for all locales (still satisfies contract).
    return {"en": text, "zh_CN": text, "zh_HK": text}


def migrate_file(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for rule in data.get("rules") or []:
        if not isinstance(rule, dict) or "message" not in rule:
            continue
        new_msg = to_i18n(rule.get("message"))
        if rule.get("message") != new_msg:
            rule["message"] = new_msg
            rule.pop("message_i18n", None)
            changed += 1
    if changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def main() -> None:
    total = 0
    files = 0
    for path in sorted(PACKAGES.rglob("governor.json")):
        n = migrate_file(path)
        if n:
            files += 1
            total += n
            print(f"{path.relative_to(REPO)}: {n} rules")
    print(f"updated {total} rules in {files} files")
    missing = []
    for path in PACKAGES.rglob("governor.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for rule in data.get("rules") or []:
            m = rule.get("message")
            if isinstance(m, str) and m.strip() and m not in TRANSLATIONS:
                missing.append(m)
    if missing:
        print("WARN untranslated fallbacks:", len(set(missing)))


if __name__ == "__main__":
    main()
