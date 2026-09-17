#!/usr/bin/env python3
"""Fill label_i18n / description_i18n / propose_guide_i18n (en, zh_CN, zh_HK).

Idempotent: merges missing locale keys; does not overwrite existing non-empty
translations unless --force.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKAGES = REPO / "packages"

# Curated UI strings. English mirrors manifest.label / description / propose_guide.
# Keys: package id → {label, description, propose_guide} each {en, zh_CN, zh_HK}
I18N: dict[str, dict[str, dict[str, str]]] = {
    "alibaba/wanx-edit": {
        "label": {
            "en": "Alibaba Wanxiang image edit",
            "zh_CN": "阿里云万相图像编辑",
            "zh_HK": "阿里雲萬相圖像編輯",
        },
        "description": {
            "en": "Edit a product/marketing image with a text prompt via Alibaba DashScope Wanxiang after Vault binding and Governor gate",
            "zh_CN": "通过阿里云 DashScope 万相，用文本提示编辑商品/营销图（需 Vault 绑定与 Governor）",
            "zh_HK": "透過阿里雲 DashScope 萬相，用文本提示編輯商品/營銷圖（需 Vault 綁定與 Governor）",
        },
        "propose_guide": {
            "en": "After the owner uploads a product photo, rewrite background/lighting/style with a prompt before social publish. Prefer image_file_id. Pair with meitu cutout and design/template-compose.",
            "zh_CN": "Owner 上传商品图后，用提示词改背景/光线/风格再发社媒。优先 image_file_id。可搭配美图抠图与 design/template-compose。",
            "zh_HK": "Owner 上傳商品圖後，用提示詞改背景/光線/風格再發社媒。優先 image_file_id。可搭配美圖摳圖與 design/template-compose。",
        },
    },
    "alpaca/place-order": {
        "label": {
            "en": "Place trade order",
            "zh_CN": "下单（Alpaca 模拟）",
            "zh_HK": "落盤（Alpaca 模擬）",
        },
        "description": {
            "en": "Submit a market order to Alpaca paper trading after Vault binding and Governor gate",
            "zh_CN": "在 Vault 绑定与 Governor 门控后，向 Alpaca 模拟盘提交市价单",
            "zh_HK": "在 Vault 綁定與 Governor 門控後，向 Alpaca 模擬盤提交市價單",
        },
        "propose_guide": {
            "en": "Gated paper trade only. Set symbol, side, and quantity from NL. Live Alpaca URLs are refused.",
            "zh_CN": "仅用于带门控的模拟交易。从自然语言设置代码、买卖方向与数量。拒绝实盘 URL。",
            "zh_HK": "僅用於帶門控的模擬交易。從自然語言設定代碼、買賣方向與數量。拒絕實盤 URL。",
        },
    },
    "canva/design-export": {
        "label": {
            "en": "Canva design export",
            "zh_CN": "Canva 设计导出",
            "zh_HK": "Canva 設計匯出",
        },
        "description": {
            "en": "Export a Canva design (PNG/JPG/PDF), optionally autofill a Brand Template first, via Connect API after Vault binding and Governor gate",
            "zh_CN": "通过 Canva Connect API 导出设计（PNG/JPG/PDF），可选先自动填充品牌模板（需 Vault 与 Governor）",
            "zh_HK": "透過 Canva Connect API 匯出設計（PNG/JPG/PDF），可選先自動填充品牌模板（需 Vault 與 Governor）",
        },
        "propose_guide": {
            "en": "Export creative from Canva. Prefer action=export with design_id. Use autofill_and_export only when Brand Template id and fields are known (Enterprise).",
            "zh_CN": "从 Canva 导出素材。优先 action=export + design_id。仅在已知品牌模板与字段时用 autofill_and_export（企业版）。",
            "zh_HK": "從 Canva 匯出素材。優先 action=export + design_id。僅在已知品牌模板與欄位時用 autofill_and_export（企業版）。",
        },
    },
    "design/template-compose": {
        "label": {
            "en": "Template product compose",
            "zh_CN": "商品卡片模板合成",
            "zh_HK": "商品卡片模板合成",
        },
        "description": {
            "en": "Compose a social-ready product card (product photo + logo + headline) into one image and a social_post artifact after Governor gate",
            "zh_CN": "将商品图+Logo+标题合成一张社媒卡片图，并产出 social_post 工件（经 Governor）",
            "zh_HK": "將商品圖+Logo+標題合成一張社媒卡片圖，並產出 social_post 工件（經 Governor）",
        },
        "propose_guide": {
            "en": "After marketing/product-promo when product+logo images exist, compose social_post (image+title+caption). Then xiaohongshu/publish under human gate. Needs Pillow on host.",
            "zh_CN": "在 marketing/product-promo 之后且有商品图+Logo 时，合成 social_post。再经人工门控发小红书。主机需 Pillow。",
            "zh_HK": "在 marketing/product-promo 之後且有商品圖+Logo 時，合成 social_post。再經人工門控發小紅書。主機需 Pillow。",
        },
    },
    "facebook/publish": {
        "label": {
            "en": "Facebook Page post",
            "zh_CN": "Facebook 主页发帖",
            "zh_HK": "Facebook 專頁發帖",
        },
        "description": {
            "en": "Post to a Facebook Page (text, optional JPEG/PNG) via Graph API after Vault binding and Governor gate",
            "zh_CN": "通过 Graph API 向 Facebook 主页发帖（文本，可选图片；需 Vault 与 Governor）",
            "zh_HK": "透過 Graph API 向 Facebook 專頁發帖（文本，可選圖片；需 Vault 與 Governor）",
        },
        "propose_guide": {
            "en": "External Page post after Internal compose: message from upstream output, not task NL verbatim. Optional image_file_id.",
            "zh_CN": "内部成文后再发主页：正文用上游结构化产出，勿直接用任务原话。可选 image_file_id。",
            "zh_HK": "內部成文後再發專頁：正文用上游結構化產出，勿直接用任務原話。可選 image_file_id。",
        },
    },
    "fred/series": {
        "label": {
            "en": "FRED series",
            "zh_CN": "FRED 宏观序列",
            "zh_HK": "FRED 宏觀序列",
        },
        "description": {
            "en": "Fetch a FRED macro time series (observations) via St. Louis Fed API for downstream compose",
            "zh_CN": "通过圣路易斯联储 FRED API 拉取宏观时间序列观测值，供下游成文",
            "zh_HK": "透過聖路易斯聯儲 FRED API 拉取宏觀時間序列觀測值，供下游成文",
        },
        "propose_guide": {
            "en": "Use when NL asks for FRED macro series (rates, CPI, DGS10, etc.). Requires Vault API key. Set series_id from NL.",
            "zh_CN": "当需要 FRED 宏观序列（利率、CPI、DGS10 等）时使用。需 Vault API key。从自然语言设置 series_id。",
            "zh_HK": "當需要 FRED 宏觀序列（利率、CPI、DGS10 等）時使用。需 Vault API key。從自然語言設定 series_id。",
        },
    },
    "general/imap": {
        "label": {
            "en": "IMAP inbox",
            "zh_CN": "IMAP 收件箱",
            "zh_HK": "IMAP 收件箱",
        },
        "description": {
            "en": "Poll an IMAP inbox (e.g. Gmail) for monitor triggers; requires Vault imap binding",
            "zh_CN": "轮询 IMAP 收件箱（如 Gmail）作为监控触发；需 Vault imap 绑定",
            "zh_HK": "輪詢 IMAP 收件箱（如 Gmail）作為監控觸發；需 Vault imap 綁定",
        },
        "propose_guide": {
            "en": "Use as monitor trigger for inbox polling. Pair with summarize / general/mail for triage.",
            "zh_CN": "用作收件箱轮询的监控触发。可搭配摘要与 general/mail 做分拣。",
            "zh_HK": "用作收件箱輪詢的監控觸發。可搭配摘要與 general/mail 做分揀。",
        },
    },
    "general/mail": {
        "label": {
            "en": "Send email",
            "zh_CN": "发送邮件",
            "zh_HK": "發送郵件",
        },
        "description": {
            "en": "Send email via SMTP after Vault binding and Governor gate",
            "zh_CN": "在 Vault 绑定与 Governor 门控后通过 SMTP 发送邮件",
            "zh_HK": "在 Vault 綁定與 Governor 門控後透過 SMTP 發送郵件",
        },
        "propose_guide": {
            "en": "External send after Internal summarize: body from upstream structured output, not task NL verbatim.",
            "zh_CN": "内部摘要后再外发：正文用上游结构化产出，勿直接用任务原话。",
            "zh_HK": "內部摘要後再外發：正文用上游結構化產出，勿直接用任務原話。",
        },
    },
    "google/ads-mutate": {
        "label": {
            "en": "Google Ads mutate",
            "zh_CN": "Google 广告变更",
            "zh_HK": "Google 廣告變更",
        },
        "description": {
            "en": "Pause/enable a Google Ads campaign; optional budget with Owner cap — no removals, after Vault binding and Governor gate",
            "zh_CN": "暂停/启用 Google Ads 广告系列；可选预算（Owner 上限）——不可删除（需 Vault 与 Governor）",
            "zh_HK": "暫停/啟用 Google Ads 廣告系列；可選預算（Owner 上限）——不可刪除（需 Vault 與 Governor）",
        },
        "propose_guide": {
            "en": "Spend-affecting write. Prefer set_status=PAUSED. ENABLED/set_budget only when NL asks and Owner caps allow. Never REMOVED. Always require_human.",
            "zh_CN": "影响花费的写入。优先暂停。启用/改预算仅当用户明确要求且未超 Owner 上限。禁止删除。必须人工确认。",
            "zh_HK": "影響花費的寫入。優先暫停。啟用/改預算僅當用戶明確要求且未超 Owner 上限。禁止刪除。必須人工確認。",
        },
    },
    "google/analytics-report": {
        "label": {
            "en": "Google Analytics 4 report",
            "zh_CN": "Google Analytics 4 报告",
            "zh_HK": "Google Analytics 4 報告",
        },
        "description": {
            "en": "Run a read-only GA4 Data API report (dimensions/metrics over a date range) after Vault binding",
            "zh_CN": "只读拉取 GA4 Data API 报告（维度/指标与日期范围；需 Vault）",
            "zh_HK": "只讀拉取 GA4 Data API 報告（維度/指標與日期範圍；需 Vault）",
        },
        "propose_guide": {
            "en": "Use before summarize when NL asks for traffic, conversions, or page performance. Prefer property_id from Vault.",
            "zh_CN": "用户问流量、转化或页面表现时，在摘要前使用。优先用 Vault 中的 property_id。",
            "zh_HK": "用戶問流量、轉化或頁面表現時，在摘要前使用。優先用 Vault 中的 property_id。",
        },
    },
    "google/meet": {
        "label": {
            "en": "Google Meet",
            "zh_CN": "Google Meet",
            "zh_HK": "Google Meet",
        },
        "description": {
            "en": "Verify Google identity for Meet workflows via OAuth userinfo after Vault binding",
            "zh_CN": "通过 OAuth userinfo 校验 Google 身份，供 Meet 相关工作流（需 Vault）",
            "zh_HK": "透過 OAuth userinfo 校驗 Google 身分，供 Meet 相關工作流（需 Vault）",
        },
        "propose_guide": {
            "en": "Use when a workflow needs Google Meet identity binding. Does not create Meet conferences.",
            "zh_CN": "工作流需要绑定 Google Meet 身份时使用。不创建会议。",
            "zh_HK": "工作流需要綁定 Google Meet 身分時使用。不建立會議。",
        },
    },
    "google/search-console": {
        "label": {
            "en": "Google Search Console",
            "zh_CN": "Google Search Console",
            "zh_HK": "Google Search Console",
        },
        "description": {
            "en": "Query Search Console search analytics (clicks, impressions, CTR, position) read-only after Vault binding",
            "zh_CN": "只读查询 Search Console 搜索分析（点击、展现、CTR、排名；需 Vault）",
            "zh_HK": "只讀查詢 Search Console 搜尋分析（點擊、展現、CTR、排名；需 Vault）",
        },
        "propose_guide": {
            "en": "Use when NL asks for SEO performance or top queries. Prefer site_url from Vault. Follow with summarize or performance-review.",
            "zh_CN": "用户问 SEO 表现或热门查询时使用。优先 Vault 的 site_url。后续可摘要或做表现复盘。",
            "zh_HK": "用戶問 SEO 表現或熱門查詢時使用。優先 Vault 的 site_url。後續可摘要或做表現複盤。",
        },
    },
    "hubspot/contact-upsert": {
        "label": {
            "en": "HubSpot contact upsert",
            "zh_CN": "HubSpot 联系人写入",
            "zh_HK": "HubSpot 聯絡人寫入",
        },
        "description": {
            "en": "Create or update a HubSpot CRM contact by email (or patch by contact_id) after Vault binding and Governor gate",
            "zh_CN": "按邮箱创建/更新 HubSpot 联系人（或按 contact_id 补丁；需 Vault 与 Governor）",
            "zh_HK": "按電郵建立/更新 HubSpot 聯絡人（或按 contact_id 補丁；需 Vault 與 Governor）",
        },
        "propose_guide": {
            "en": "Upsert CRM contacts from leads/forms. Prefer email for find-or-create. Notes → hubspot/crm-note.",
            "zh_CN": "从线索/表单写入 CRM 联系人。优先用邮箱查找或创建。备注用 hubspot/crm-note。",
            "zh_HK": "從線索/表單寫入 CRM 聯絡人。優先用電郵查找或建立。備註用 hubspot/crm-note。",
        },
    },
    "hubspot/crm-note": {
        "label": {
            "en": "HubSpot CRM note",
            "zh_CN": "HubSpot CRM 备注",
            "zh_HK": "HubSpot CRM 備註",
        },
        "description": {
            "en": "Create a HubSpot CRM note on a contact (by contact_id or email upsert) after Vault binding and Governor gate",
            "zh_CN": "在联系人上创建 HubSpot CRM 备注（按 contact_id 或邮箱；需 Vault 与 Governor）",
            "zh_HK": "在聯絡人上建立 HubSpot CRM 備註（按 contact_id 或電郵；需 Vault 與 Governor）",
        },
        "propose_guide": {
            "en": "Log marketing/sales handoff notes after research or meetings. Prefer contact_id when known.",
            "zh_CN": "调研或会议后记录营销/销售交接备注。已知 contact_id 时优先使用。",
            "zh_HK": "調研或會議後記錄營銷/銷售交接備註。已知 contact_id 時優先使用。",
        },
    },
    "instagram/publish": {
        "label": {
            "en": "Instagram Feed post",
            "zh_CN": "Instagram Feed 发帖",
            "zh_HK": "Instagram Feed 發帖",
        },
        "description": {
            "en": "Publish one Feed image post to an Instagram professional account via Graph API after Vault binding and Governor gate",
            "zh_CN": "向 Instagram 专业账号发布一张 Feed 图片帖（Graph API；需 Vault 与 Governor）",
            "zh_HK": "向 Instagram 專業帳號發佈一張 Feed 圖片帖（Graph API；需 Vault 與 Governor）",
        },
        "propose_guide": {
            "en": "External Feed post after compose: caption from upstream. Image required (JPEG/PNG). Do not share Vault with facebook/publish.",
            "zh_CN": "成文后发 Feed：文案用上游产出。必须有图（JPEG/PNG）。勿与 facebook/publish 共用 Vault。",
            "zh_HK": "成文後發 Feed：文案用上游產出。必須有圖（JPEG/PNG）。勿與 facebook/publish 共用 Vault。",
        },
    },
    "klaviyo/campaign": {
        "label": {
            "en": "Klaviyo campaign",
            "zh_CN": "Klaviyo 邮件活动",
            "zh_HK": "Klaviyo 郵件活動",
        },
        "description": {
            "en": "Create a Klaviyo email campaign with HTML template (optional send) after Vault binding and Governor gate",
            "zh_CN": "创建带 HTML 模板的 Klaviyo 邮件活动（可选发送；需 Vault 与 Governor）",
            "zh_HK": "建立帶 HTML 模板的 Klaviyo 郵件活動（可選發送；需 Vault 與 Governor）",
        },
        "propose_guide": {
            "en": "Ecommerce/lifecycle email after compose. Default creates without sending. send/create_and_send only when NL explicitly asks.",
            "zh_CN": "成文后做电商/生命周期邮件。默认只创建不发送。仅当用户明确要求发送时才 send。",
            "zh_HK": "成文後做電商/生命周期郵件。預設只建立不發送。僅當用戶明確要求發送時才 send。",
        },
    },
    "linkedin/publish": {
        "label": {
            "en": "LinkedIn Company Page post",
            "zh_CN": "LinkedIn 公司页发帖",
            "zh_HK": "LinkedIn 公司頁發帖",
        },
        "description": {
            "en": "Post to a LinkedIn Company Page (text, optional JPEG/PNG) via the Posts API after Vault binding and Governor gate",
            "zh_CN": "通过 Posts API 向 LinkedIn 公司页发帖（文本，可选图片；需 Vault 与 Governor）",
            "zh_HK": "透過 Posts API 向 LinkedIn 公司頁發帖（文本，可選圖片；需 Vault 與 Governor）",
        },
        "propose_guide": {
            "en": "External Company Page post after compose: commentary from upstream, not task NL. Optional image_file_id.",
            "zh_CN": "成文后发公司页：正文用上游产出，勿用任务原话。可选 image_file_id。",
            "zh_HK": "成文後發公司頁：正文用上游產出，勿用任務原話。可選 image_file_id。",
        },
    },
    "mailchimp/campaign": {
        "label": {
            "en": "Mailchimp campaign",
            "zh_CN": "Mailchimp 邮件活动",
            "zh_HK": "Mailchimp 郵件活動",
        },
        "description": {
            "en": "Create a Mailchimp regular campaign with HTML/text content, optionally send after Vault binding and Governor gate",
            "zh_CN": "创建 Mailchimp 常规邮件活动（HTML/文本），可选发送（需 Vault 与 Governor）",
            "zh_HK": "建立 Mailchimp 常規郵件活動（HTML/文本），可選發送（需 Vault 與 Governor）",
        },
        "propose_guide": {
            "en": "Audience email after compose. Default saves campaign only. send/create_and_send only when NL explicitly asks.",
            "zh_CN": "成文后做受众邮件。默认只保存活动。仅当用户明确要求时发送。",
            "zh_HK": "成文後做受眾郵件。預設只保存活動。僅當用戶明確要求時發送。",
        },
    },
    "marketing/ab-copy": {
        "label": {
            "en": "Marketing A/B copy",
            "zh_CN": "营销 A/B 文案",
            "zh_HK": "營銷 A/B 文案",
        },
        "description": {
            "en": "Propose A/B (or multi-variant) marketing copy from a brief or draft for later human-gated publish connectors",
            "zh_CN": "根据简报或草稿提出 A/B（或多变体）营销文案，供后续人工门控发布",
            "zh_HK": "根據簡報或草稿提出 A/B（或多變體）營銷文案，供後續人工門控發佈",
        },
        "propose_guide": {
            "en": "After campaign-brief or brand-voice when NL asks for A/B variants. Emit Internal variants — do not publish.",
            "zh_CN": "在活动简报或品牌语气之后，用户要 A/B 变体时使用。产出内部变体——不外发。",
            "zh_HK": "在活動簡報或品牌語氣之後，用戶要 A/B 變體時使用。產出內部變體——不外發。",
        },
    },
    "marketing/brand-voice": {
        "label": {
            "en": "Marketing brand voice",
            "zh_CN": "营销品牌语气",
            "zh_HK": "營銷品牌語氣",
        },
        "description": {
            "en": "Propose or apply a brand-voice checklist (tone, do/don't, banned phrases) before external compose or publish",
            "zh_CN": "在外发成文/发布前提出或套用品牌语气清单（调性、宜忌、禁用词）",
            "zh_HK": "在外發成文/發佈前提出或套用品牌語氣清單（調性、宜忌、禁用詞）",
        },
        "propose_guide": {
            "en": "When NL mentions brand voice/tone or before publish. Emit Internal checklist; feed banned phrases into Owner governors.",
            "zh_CN": "用户提到品牌语气/调性或发布前使用。产出内部清单；禁用词可写入 Owner governor。",
            "zh_HK": "用戶提到品牌語氣/調性或發佈前使用。產出內部清單；禁用詞可寫入 Owner governor。",
        },
    },
    "marketing/campaign-brief": {
        "label": {
            "en": "Marketing campaign brief",
            "zh_CN": "营销活动简报",
            "zh_HK": "營銷活動簡報",
        },
        "description": {
            "en": "Propose a structured marketing campaign brief (goal, audience, offer, channels, KPIs, timeline)",
            "zh_CN": "提出结构化营销活动简报（目标、受众、卖点、渠道、KPI、时间线）",
            "zh_HK": "提出結構化營銷活動簡報（目標、受眾、賣點、渠道、KPI、時間線）",
        },
        "propose_guide": {
            "en": "Early when NL asks to plan a campaign/launch/promo. Emit Internal structured fields — do not publish.",
            "zh_CN": "用户要策划活动/上线/促销时尽早使用。产出内部结构字段——不外发。",
            "zh_HK": "用戶要策劃活動/上線/促銷時儘早使用。產出內部結構欄位——不外發。",
        },
    },
    "marketing/channel-mix": {
        "label": {
            "en": "Marketing channel mix",
            "zh_CN": "营销渠道组合",
            "zh_HK": "營銷渠道組合",
        },
        "description": {
            "en": "Propose which owned/paid/earned channels to use for a brief (and which repertoire connectors to attach next)",
            "zh_CN": "根据简报建议自有/付费/赢得渠道，并点名下一步可接的 repertoire 连接器",
            "zh_HK": "根據簡報建議自有/付費/贏得渠道，並點名下一步可接的 repertoire 連接器",
        },
        "propose_guide": {
            "en": "After campaign-brief when NL asks which channels. Recommend 2–4 channels and connectors — do not invoke write-external here.",
            "zh_CN": "活动简报后用户问用哪些渠道时使用。建议 2–4 个渠道与连接器——此处不调用写外联。",
            "zh_HK": "活動簡報後用戶問用哪些渠道時使用。建議 2–4 個渠道與連接器——此處不呼叫寫外聯。",
        },
    },
    "marketing/content-calendar": {
        "label": {
            "en": "Marketing content calendar",
            "zh_CN": "营销内容日历",
            "zh_HK": "營銷內容日曆",
        },
        "description": {
            "en": "Propose a week/month content calendar (themes, channels, cadence) from a campaign brief",
            "zh_CN": "根据活动简报提出周/月内容日历（主题、渠道、节奏）",
            "zh_HK": "根據活動簡報提出週/月內容日曆（主題、渠道、節奏）",
        },
        "propose_guide": {
            "en": "After brief/channel-mix when NL asks for calendar or posting cadence. Emit Internal calendar — do not publish.",
            "zh_CN": "简报/渠道组合后用户要日历或发布节奏时使用。产出内部日历——不外发。",
            "zh_HK": "簡報/渠道組合後用戶要日曆或發佈節奏時使用。產出內部日曆——不外發。",
        },
    },
    "marketing/hiring-campaign": {
        "label": {
            "en": "Hiring campaign",
            "zh_CN": "招聘营销计划",
            "zh_HK": "招聘營銷計劃",
        },
        "description": {
            "en": "Propose an employer-brand / recruiting marketing plan (roles, audience, channels, compliance)",
            "zh_CN": "提出雇主品牌/招聘营销计划（岗位、受众、渠道、合规）",
            "zh_HK": "提出僱主品牌/招聘營銷計劃（崗位、受眾、渠道、合規）",
        },
        "propose_guide": {
            "en": "When NL asks for hiring/employer-brand/campus recruit plan. Emit Internal structure; writes go to gated connectors.",
            "zh_CN": "用户要招聘/雇主品牌/校园招聘计划时使用。产出内部结构；外发走带门控连接器。",
            "zh_HK": "用戶要招聘/僱主品牌/校園招聘計劃時使用。產出內部結構；外發走帶門控連接器。",
        },
    },
    "marketing/local-store": {
        "label": {
            "en": "Local store campaign",
            "zh_CN": "本地门店营销计划",
            "zh_HK": "本地門店營銷計劃",
        },
        "description": {
            "en": "Propose a local / multi-location retail or hospitality marketing plan (geo, offers, channels, compliance)",
            "zh_CN": "提出本地/多门店零售或餐饮酒店营销计划（地理、优惠、渠道、合规）",
            "zh_HK": "提出本地/多門店零售或餐飲酒店營銷計劃（地理、優惠、渠道、合規）",
        },
        "propose_guide": {
            "en": "When NL asks for local store/restaurant/clinic/geo promo plan. Emit Internal structure — do not publish here.",
            "zh_CN": "用户要本地门店/餐饮/诊所/地理促销计划时使用。产出内部结构——此处不外发。",
            "zh_HK": "用戶要本地門店/餐飲/診所/地理促銷計劃時使用。產出內部結構——此處不外發。",
        },
    },
    "marketing/performance-review": {
        "label": {
            "en": "Marketing performance review",
            "zh_CN": "营销表现复盘",
            "zh_HK": "營銷表現複盤",
        },
        "description": {
            "en": "Propose a performance review / learnings brief from analytics or ads report content",
            "zh_CN": "根据分析或广告报告内容提出表现复盘/学习要点",
            "zh_HK": "根據分析或廣告報告內容提出表現複盤/學習要點",
        },
        "propose_guide": {
            "en": "After GA4/GSC/Meta insights when NL asks what worked. Emit Internal wins/lags/next experiments — do not mutate ads.",
            "zh_CN": "在 GA4/GSC/Meta 洞察之后，用户问效果如何时使用。产出内部得失与下一步——不改广告。",
            "zh_HK": "在 GA4/GSC/Meta 洞察之後，用戶問效果如何時使用。產出內部得失與下一步——不改廣告。",
        },
    },
    "marketing/product-promo": {
        "label": {
            "en": "Product promo card",
            "zh_CN": "单品促销卡片文案",
            "zh_HK": "單品促銷卡片文案",
        },
        "description": {
            "en": "Propose short product promo copy and layout hints for template compose and Xiaohongshu publish",
            "zh_CN": "提出短促商品促销文案与版式提示，供模板合成与小红书发布",
            "zh_HK": "提出短促商品促銷文案與版式提示，供模板合成與小紅書發佈",
        },
        "propose_guide": {
            "en": "When NL uploads a product photo with store/logo/style. Emit Internal social_post fields — do not publish. Next: template-compose → xiaohongshu/publish.",
            "zh_CN": "用户上传商品图且有店名/Logo/风格时使用。产出内部 social_post 字段——不外发。下一步：模板合成→小红书。",
            "zh_HK": "用戶上傳商品圖且有店名/Logo/風格時使用。產出內部 social_post 欄位——不外發。下一步：模板合成→小紅書。",
        },
    },
    "meitu/product-image": {
        "label": {
            "en": "Meitu product image",
            "zh_CN": "美图商品图处理",
            "zh_HK": "美圖商品圖處理",
        },
        "description": {
            "en": "Cut out product subjects via Meitu AI Open Platform MTlab sync API after Vault binding and Governor gate",
            "zh_CN": "通过美图开放平台 MTlab 同步 API 抠商品主体（需 Vault 与 Governor）",
            "zh_HK": "透過美圖開放平台 MTlab 同步 API 摳商品主體（需 Vault 與 Governor）",
        },
        "propose_guide": {
            "en": "Mainland SMB product photo cutout before social. Default action=cutout. Pair with wanx-edit then publish.",
            "zh_CN": "内地中小商家商品图发社媒前抠图。默认 action=cutout。可接万相编辑再发布。",
            "zh_HK": "內地中小商家商品圖發社媒前摳圖。預設 action=cutout。可接萬相編輯再發佈。",
        },
    },
    "meta/ads-insights": {
        "label": {
            "en": "Meta Ads insights",
            "zh_CN": "Meta 广告洞察",
            "zh_HK": "Meta 廣告洞察",
        },
        "description": {
            "en": "Read Meta Marketing API ad account insights (spend, impressions, clicks, CPA) — read-only, no bid changes",
            "zh_CN": "只读 Meta Marketing API 广告账户洞察（花费、展现、点击、CPA）——不改出价",
            "zh_HK": "只讀 Meta Marketing API 廣告帳戶洞察（花費、展現、點擊、CPA）——不改出價",
        },
        "propose_guide": {
            "en": "When NL asks Meta/FB/IG ads performance. Read-only. Prefer follow-up marketing/performance-review.",
            "zh_CN": "用户问 Meta/FB/IG 广告表现时使用。只读。建议后续做营销复盘。",
            "zh_HK": "用戶問 Meta/FB/IG 廣告表現時使用。只讀。建議後續做營銷複盤。",
        },
    },
    "meta/ads-mutate": {
        "label": {
            "en": "Meta Ads mutate",
            "zh_CN": "Meta 广告变更",
            "zh_HK": "Meta 廣告變更",
        },
        "description": {
            "en": "Pause/activate Meta campaign, ad set, or ad; optional daily_budget with Owner cap — no deletes",
            "zh_CN": "暂停/启用 Meta 广告系列/组/广告；可选日预算（Owner 上限）——不可删除",
            "zh_HK": "暫停/啟用 Meta 廣告系列/組/廣告；可選日預算（Owner 上限）——不可刪除",
        },
        "propose_guide": {
            "en": "Spend-affecting write. Prefer PAUSED. ACTIVE/set_budget only when NL asks and caps allow. Never DELETE. require_human.",
            "zh_CN": "影响花费的写入。优先暂停。启用/改预算仅当用户明确要求且未超上限。禁止删除。须人工确认。",
            "zh_HK": "影響花費的寫入。優先暫停。啟用/改預算僅當用戶明確要求且未超上限。禁止刪除。須人工確認。",
        },
    },
    "microsoft/teams": {
        "label": {
            "en": "Microsoft Teams",
            "zh_CN": "Microsoft Teams",
            "zh_HK": "Microsoft Teams",
        },
        "description": {
            "en": "Verify Microsoft identity for Teams workflows via Graph /me after Vault binding",
            "zh_CN": "通过 Graph /me 校验 Microsoft 身份，供 Teams 工作流（需 Vault）",
            "zh_HK": "透過 Graph /me 校驗 Microsoft 身分，供 Teams 工作流（需 Vault）",
        },
        "propose_guide": {
            "en": "When a workflow needs Microsoft Teams identity binding. Does not create Teams meetings.",
            "zh_CN": "工作流需要绑定 Teams 身份时使用。不创建会议。",
            "zh_HK": "工作流需要綁定 Teams 身分時使用。不建立會議。",
        },
    },
    "notion/pages": {
        "label": {
            "en": "Notion",
            "zh_CN": "Notion 页面",
            "zh_HK": "Notion 頁面",
        },
        "description": {
            "en": "Create a Notion page (or database row) via Notion API after Vault binding and Governor gate",
            "zh_CN": "通过 Notion API 创建页面（或数据库行；需 Vault 与 Governor）",
            "zh_HK": "透過 Notion API 建立頁面（或資料庫列；需 Vault 與 Governor）",
        },
        "propose_guide": {
            "en": "Write Notion after Internal extract/summarize. Title and body from upstream, not task NL verbatim.",
            "zh_CN": "内部抽取/摘要后写入 Notion。标题与正文用上游产出，勿用任务原话。",
            "zh_HK": "內部抽取/摘要後寫入 Notion。標題與正文用上游產出，勿用任務原話。",
        },
    },
    "tavily/web-search": {
        "label": {
            "en": "Web research",
            "zh_CN": "网页检索（Tavily）",
            "zh_HK": "網頁檢索（Tavily）",
        },
        "description": {
            "en": "Search the public web via Tavily and return ranked snippets for downstream summarize steps",
            "zh_CN": "通过 Tavily 搜索公开网页，返回排序摘要片段供下游摘要",
            "zh_HK": "透過 Tavily 搜尋公開網頁，返回排序摘要片段供下游摘要",
        },
        "propose_guide": {
            "en": "Separate step before summarize when NL asks to search the web. Set query when NL states a fixed theme. For deeper bodies use searxng + crawl4ai.",
            "zh_CN": "用户要搜网页时，在摘要前单独一步。有固定主题则设置 query。要全文用 searxng + crawl4ai。",
            "zh_HK": "用戶要搜網頁時，在摘要前單獨一步。有固定主題則設定 query。要全文用 searxng + crawl4ai。",
        },
    },
    "tiktok/publish": {
        "label": {
            "en": "TikTok video publish",
            "zh_CN": "TikTok 视频发布",
            "zh_HK": "TikTok 影片發佈",
        },
        "description": {
            "en": "Upload a TikTok video via Content Posting API (inbox draft by default; optional direct post)",
            "zh_CN": "通过内容发布 API 上传 TikTok 视频（默认收件箱草稿；可选直发）",
            "zh_HK": "透過內容發佈 API 上傳 TikTok 影片（預設收件箱草稿；可選直發）",
        },
        "propose_guide": {
            "en": "Push composed video. Default mode=inbox. mode=direct only when NL asks and Owner allows. Prefer video_file_id.",
            "zh_CN": "推送成片。默认 inbox。仅当用户明确要求且 Owner 允许时用 direct。优先 video_file_id。",
            "zh_HK": "推送成片。預設 inbox。僅當用戶明確要求且 Owner 允許時用 direct。優先 video_file_id。",
        },
    },
    "twitter/publish": {
        "label": {
            "en": "Twitter / X post",
            "zh_CN": "Twitter / X 发帖",
            "zh_HK": "Twitter / X 發帖",
        },
        "description": {
            "en": "Post one tweet (text, optional JPEG/PNG) via X API after Vault binding and Governor gate",
            "zh_CN": "通过 X API 发一条推文（文本，可选图片；需 Vault 与 Governor）",
            "zh_HK": "透過 X API 發一則推文（文本，可選圖片；需 Vault 與 Governor）",
        },
        "propose_guide": {
            "en": "External post after compose: tweet body from upstream, not task NL. Optional image_file_id.",
            "zh_CN": "成文后外发：推文正文用上游产出，勿用任务原话。可选 image_file_id。",
            "zh_HK": "成文後外發：推文正文用上游產出，勿用任務原話。可選 image_file_id。",
        },
    },
    "webflow/cms-publish": {
        "label": {
            "en": "Webflow CMS item",
            "zh_CN": "Webflow CMS 条目",
            "zh_HK": "Webflow CMS 條目",
        },
        "description": {
            "en": "Create a Webflow CMS collection item (staged draft by default, optional live publish)",
            "zh_CN": "创建 Webflow CMS 集合条目（默认暂存草稿，可选上线）",
            "zh_HK": "建立 Webflow CMS 集合條目（預設暫存草稿，可選上線）",
        },
        "propose_guide": {
            "en": "CMS copy after compose on Webflow sites. Default staged. publish=true only when NL asks to go live.",
            "zh_CN": "Webflow 站点成文后写 CMS。默认暂存。仅当用户明确要求上线时 publish=true。",
            "zh_HK": "Webflow 站點成文後寫 CMS。預設暫存。僅當用戶明確要求上線時 publish=true。",
        },
    },
    "wordpress/post": {
        "label": {
            "en": "WordPress post",
            "zh_CN": "WordPress 文章",
            "zh_HK": "WordPress 文章",
        },
        "description": {
            "en": "Create a WordPress post via REST API (draft by default, optional publish)",
            "zh_CN": "通过 REST API 创建 WordPress 文章（默认草稿，可选发布）",
            "zh_HK": "透過 REST API 建立 WordPress 文章（預設草稿，可選發佈）",
        },
        "propose_guide": {
            "en": "Blog/landing copy after compose. Default draft. status=publish only when NL explicitly asks.",
            "zh_CN": "成文后发博客/落地页。默认草稿。仅当用户明确要求时发布。",
            "zh_HK": "成文後發網誌/落地頁。預設草稿。僅當用戶明確要求時發佈。",
        },
    },
    "xiaohongshu/publish": {
        "label": {
            "en": "Xiaohongshu note publish",
            "zh_CN": "小红书笔记发布",
            "zh_HK": "小紅書筆記發佈",
        },
        "description": {
            "en": "Publish an image note to Xiaohongshu (RED) via Owner-configured OpenAPI gateway",
            "zh_CN": "通过 Owner 配置的 OpenAPI 网关向小红书发布图文笔记",
            "zh_HK": "透過 Owner 配置的 OpenAPI 閘道向小紅書發佈圖文筆記",
        },
        "propose_guide": {
            "en": "After template-compose/compose. Prefer upstream title/caption/image. Do not scrape creator web. Always require_human.",
            "zh_CN": "模板合成/成文后使用。优先上游标题/文案/图。勿爬创作者网页。必须人工确认。",
            "zh_HK": "模板合成/成文後使用。優先上游標題/文案/圖。勿爬創作者網頁。必須人工確認。",
        },
    },
    "youtube/publish": {
        "label": {
            "en": "YouTube video upload",
            "zh_CN": "YouTube 视频上传",
            "zh_HK": "YouTube 影片上傳",
        },
        "description": {
            "en": "Upload a video to YouTube via Data API v3 resumable upload (default privacy=unlisted)",
            "zh_CN": "通过 Data API v3 可续传上传 YouTube 视频（默认隐私=不公开列出）",
            "zh_HK": "透過 Data API v3 可續傳上傳 YouTube 影片（預設私隱=不公開列出）",
        },
        "propose_guide": {
            "en": "Upload composed video. Requires video_file_id. Default unlisted — public only when NL asks.",
            "zh_CN": "上传成片。需要 video_file_id。默认不公开列出——仅当用户明确要求时公开。",
            "zh_HK": "上傳成片。需要 video_file_id。預設不公開列出——僅當用戶明確要求時公開。",
        },
    },
    "zoom/account": {
        "label": {
            "en": "Zoom",
            "zh_CN": "Zoom",
            "zh_HK": "Zoom",
        },
        "description": {
            "en": "Verify Zoom identity via Server-to-Server OAuth or bearer token (GET /v2/users/me)",
            "zh_CN": "通过 Server-to-Server OAuth 或 bearer 校验 Zoom 身份（GET /v2/users/me）",
            "zh_HK": "透過 Server-to-Server OAuth 或 bearer 校驗 Zoom 身分（GET /v2/users/me）",
        },
        "propose_guide": {
            "en": "Use when a workflow needs Zoom identity binding via users/me. Does not create meetings.",
            "zh_CN": "工作流需要通过 users/me 绑定 Zoom 身份时使用。不创建会议。",
            "zh_HK": "工作流需要透過 users/me 綁定 Zoom 身分時使用。不建立會議。",
        },
    },
}


LOCALES = ("en", "zh_CN", "zh_HK")
FIELDS = (
    ("label", "label_i18n"),
    ("description", "description_i18n"),
    ("propose_guide", "propose_guide_i18n"),
)


def _merge_i18n(
    existing: dict | None,
    curated: dict[str, str],
    english_fallback: str,
    *,
    force: bool,
) -> dict[str, str]:
    out: dict[str, str] = {}
    base = existing if isinstance(existing, dict) else {}
    for loc in LOCALES:
        curated_val = (curated or {}).get(loc) or ""
        old = str(base.get(loc) or "").strip()
        if force or not old:
            if loc == "en":
                out[loc] = curated_val or english_fallback or old
            else:
                out[loc] = curated_val or old
        else:
            out[loc] = old
        if not out[loc] and loc == "en":
            out[loc] = english_fallback
    return out


def migrate_manifest(path: Path, *, force: bool, dry_run: bool) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    cid = str(data.get("id") or "")
    curated = I18N.get(cid)
    changed = False

    # Packages already fully curated elsewhere (searxng etc.) still ensure keys exist
    for src_key, i18n_key in FIELDS:
        en_val = str(data.get(src_key) or "").strip()
        block = (curated or {}).get(src_key.replace("propose_guide", "propose_guide"), {})
        # normalize: curated uses propose_guide key
        if src_key == "propose_guide":
            block = (curated or {}).get("propose_guide") or {}
        elif src_key == "label":
            block = (curated or {}).get("label") or {}
        elif src_key == "description":
            block = (curated or {}).get("description") or {}

        if not en_val and not block:
            continue
        if not en_val and block.get("en"):
            # fill missing English propose_guide for zoom etc.
            data[src_key] = block["en"]
            en_val = block["en"]
            changed = True

        new_block = _merge_i18n(data.get(i18n_key), block, en_val, force=force)
        if data.get(i18n_key) != new_block:
            # Prefer placing i18n right after English field
            data[i18n_key] = new_block
            changed = True

    if not changed:
        return False
    if dry_run:
        print(f"DRY {cid}")
        return True

    # Rebuild key order: insert i18n after English field
    ordered: dict = {}
    for k, v in data.items():
        if k in {"label_i18n", "description_i18n", "propose_guide_i18n"}:
            continue
        ordered[k] = v
        if k == "label" and "label_i18n" in data:
            ordered["label_i18n"] = data["label_i18n"]
        if k == "description" and "description_i18n" in data:
            ordered["description_i18n"] = data["description_i18n"]
        if k == "propose_guide" and "propose_guide_i18n" in data:
            ordered["propose_guide_i18n"] = data["propose_guide_i18n"]
    for k in ("label_i18n", "description_i18n", "propose_guide_i18n"):
        if k in data and k not in ordered:
            ordered[k] = data[k]

    path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK {cid}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="Overwrite existing zh_* translations")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    n = 0
    for path in sorted(PACKAGES.glob("*/**/manifest.json")):
        if "_template" in path.parts:
            continue
        if migrate_manifest(path, force=args.force, dry_run=args.dry_run):
            n += 1
    print(f"updated={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
