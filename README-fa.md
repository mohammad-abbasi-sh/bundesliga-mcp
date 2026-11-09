# bundesliga-mcp ⚽

سرور MCP **غیررسمی و فقط‌خواندنی** برای **فوتبال آلمان** از طریق API رایگان [OpenLigaDB](https://api.openligadb.de) — برنامهٔ بازی‌های بوندس‌لیگا، نتایج زنده، جدول و گلزن‌ها. بدون کلید، بدون لاگین.

> ساختهٔ محمد عباسی در چارچوب «کارخانهٔ MCP آلمان» (به سبک سپهر). وابسته به OpenLigaDB یا DFL نیست.

## برای ایجنت‌های هوش مصنوعی

به تنظیمات MCP اضافه کنید (stdio):

```json
{
  "mcpServers": {
    "bundesliga": {
      "command": "uvx",
      "args": ["bundesliga-mcp"]
    }
  }
}
```

یا اجرای محلی: `python -m bundesliga_mcp.server` (نیازمند `mcp<2` و `httpx`).

## ابزارها

| ابزار | توضیح |
|------|------|
| `bundesliga_list_leagues` | لیگ‌ها با فصل جاری — bl1, bl2, bl3, dfb, del, bbl, hbl |
| `bundesliga_get_fixtures` | بازی‌های یک هفته — `league` (پیش‌فرض bl1)، `season` (پیش‌فرض فصل جاری، مثل «2026»)، `matchday` (پیش‌فرض هفتهٔ جاری، ۱ تا ۳۴) |
| `bundesliga_get_live_scores` | هفتهٔ جاری: نتیجه + وضعیت (finished/live/scheduled) هر بازی — `league` |
| `bundesliga_get_table` | جدول لیگ — `league`، `season` (پیش‌فرض فصل جاری) |
| `bundesliga_get_top_scorers` | گلزن‌های برتر یک فصل — `league`، `season` (پیش‌فرض فصل جاری)، `limit` از ۱ تا ۵۰ |
| `bundesliga_get_match_detail` | جزئیات کامل یک بازی (نتیجه، گل‌ها با دقیقه و گلزن، ورزشگاه) — `match_id`، `league`، `season` |

نکته‌ها:
- فصل به‌صورت پیش‌فرض فصل جاری است (زنده از فهرست لیگ‌ها پیدا می‌شود)؛ هفته هم هفتهٔ جاری است.
- گلزن‌ها از رویدادهای گل هر بازی شمرده می‌شوند (گل‌به‌خودی حساب نمی‌شود) — چون اندپوینت گلزن‌های خود API خطای 404 می‌دهد.
- `bbl` و `hbl` هنوز ورودی لیگ ندارند — ابزارهایشان تا وقتی OpenLigaDB منتشرشان کند نتیجهٔ خالی برمی‌گردانند. DEL (هاکی روی یخ) مثل لیگ‌های فوتبال کار می‌کند.
- داده: API عمومی OpenLigaDB — بدون کلید، بدون لاگین، فقط‌خواندنی. داده تحت مجوز Open Database License (ODbL) است.

## توسعه

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_football.py` — آفلاین، با پاسخ‌های واقعی ضبط‌شده از API (۲۰ تست)
- `tests/test_live.py` — چند درخواست زندهٔ محتاطانه به api.openligadb.de (۷ تست)

تست‌ها: ۲۷ از ۲۷ سبز (۲۰ آفلاین + ۷ زنده، ۲۰۲۶-۱۱-۰۹).

## مجوز

MIT
