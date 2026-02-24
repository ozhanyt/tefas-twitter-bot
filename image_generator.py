import os
import json
import asyncio
import subprocess
from playwright.async_api import async_playwright
from datetime import datetime

# Translation/Formatting Helpers
def format_money(val):
    sign = "+" if val >= 0 else "-"
    abs_val = abs(val)
    # Full value format: +₺639.945.848
    v_str = f"{abs_val:,.0f}".replace(",", ".")
    return f"{sign}₺{v_str}"

def format_pct(val, decimals=2):
    fmt = "{:." + str(decimals) + "f}%"
    return fmt.format(val).replace(".", ",")

def format_turkish_date(date_str):
    months = {
        "01": "Ocak", "02": "Şubat", "03": "Mart", "04": "Nisan",
        "05": "Mayıs", "06": "Haziran", "07": "Temmuz", "08": "Ağustos",
        "09": "Eylül", "10": "Ekim", "11": "Kasım", "12": "Aralık"
    }
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.day} {months[dt.strftime('%m')]} {dt.year}"
    except:
        return date_str

def generate_fund_list_html(funds, is_inflow=True, sort_mode='tl'):
    html = ""
    for f in funds:
        trend_class = "trend-up" if is_inflow else "trend-down"
        val = f['net_flow'] if 'net_flow' in f else f.get('return_pct', 0)
        
        if sort_mode == 'tl' and 'net_flow' in f:
            val_str = format_money(val)
            pct_val = f.get('flow_pct', f.get('return_pct', 0))
            # Resim 1 style: (+1,17%)
            sign = "+" if pct_val >= 0 else "" # format_pct might handle or we add manually
            pct_str = f"({sign}{format_pct(pct_val)})"
        else:
            val_str = format_pct(f.get('return_pct', 0))
            pct_str = ""
            
        name = f.get('name', f.get('fund_name', ''))
        
        html += f"""
        <li class="fund-item">
            <div class="f-left">
                <span class="f-code">{f['fund_code']}</span>
                <span class="f-name">{name}</span>
            </div>
            <div class="f-right">
                <span class="f-val {trend_class}">{val_str}</span>
                <span class="f-pct {trend_class}">{pct_str}</span>
            </div>
        </li>
        """
    return html

def generate_investor_list_html(funds):
    html = ""
    for f in funds:
        inv_pct = f.get('inv_change_pct', 0)   # was: 'inv_pct' — field is saved as 'inv_change_pct' by data_fetcher
        inv_change = f.get('inv_change', 0)
        val_class = "trend-up" if inv_change >= 0 else "trend-down"
        inv_str = f"{inv_change:+d}"
        pct_prefix = "+" if inv_pct >= 0 else ""
        
        name = f.get('name', f.get('fund_name', ''))
        
        html += f"""
        <li class="fund-item">
            <div class="f-left">
                <span class="f-code">{f['fund_code']}</span>
                <span class="f-name">{name}</span>
            </div>
            <div class="f-right">
                <div class="val {val_class}">{inv_str} Kişi</div>
                <div class="pct {val_class}">({pct_prefix}{format_pct(inv_pct)})</div>
            </div>
        </li>
        """
    return html

def generate_predictions_html(predictions):
    html = ""
    for p in predictions:
        code = p.get('code', '').upper()
        val = p.get('val', '')
        desc = p.get('desc', '')
        if not code and not val: continue
        
        # Resim 1 & 2 style: Dark background, stacked code and desc
        val_str = val if "%" in val else f"%{val}"
        
        # Check if negative for coloring
        is_negative = "-" in val
        trend_class = "trend-down" if is_negative else "trend-up"
        
        html += f"""
        <div class="pred-item fund-item">
            <div class="f-left">
                <span class="f-code">{code}</span>
                <span class="f-name">{desc}</span>
            </div>
            <div class="f-right">
                <span class="f-val {trend_class}">{val_str}</span>
            </div>
        </div>
        """
    return html

def generate_portfolio_diff_html(diffs_dict, config):
    html = ""
    if not diffs_dict: return html
    
    # Target the specific fund from config
    target_fund = config.get("portfolio_diff_fund", "PHE").upper()
    
    # Fallback to the first available if not found
    if target_fund not in diffs_dict:
        target_fund = list(diffs_dict.keys())[0] if diffs_dict else None
        
    if not target_fund:
        return ""
        
    data = diffs_dict[target_fund]
    allocations = data.get("allocations", [])
    
    for alloc in allocations:
        asset = alloc.get("asset", "")
        w = alloc.get("weight", 0)
        d = alloc.get("diff", 0)
        
        if abs(d) < 0.01:
            diff_str = "(-)"
            trend_class = "trend-neutral"
            sign = ""
        else:
            sign = "+" if d > 0 else ""
            diff_str = f"({sign}%{d:.2f})".replace(".", ",")
            trend_class = "trend-up" if d > 0 else "trend-down"
            
        weight_str = f"%{w:.2f}".replace(".", ",")
        
        html += f"""
        <li class="fund-item portfolio-fund-item">
            <div class="f-left">
                <span class="f-name">{asset}</span>
            </div>
            <div class="f-right">
                <span class="f-val">{weight_str}</span>
                <span class="f-pct {trend_class}">{diff_str}</span>
            </div>
        </li>
        """
    return html

def generate_tracked_html(tracked_dict, period_label):
    html = ""
    # We expect data like: { "TLY": { "price": ..., "period_flow": ..., "period_return_pct": ..., "inv_change": ..., "total_size": ... } }
    for code, data in tracked_dict.items():
        price = data.get('price', 0)
        p_flow = data.get('period_flow', 0)
        p_ret = data.get('period_return_pct', 0)
        inv_change = data.get('period_investor_change', 0)   # was: inv_change
        inv_pct = data.get('period_investor_pct', 0)         # was: inv_pct
        total_size = data.get('fund_size', 0)                # was: total_size
        flow_pct = data.get('period_flow_pct', 0)            # was: flow_pct

        price_str = f"₺{price:,.6f}".replace(",", "X").replace(".", ",").replace("X", ".")
        flow_str = format_money(p_flow)
        flow_class = "trend-up" if p_flow >= 0 else "trend-down"
        flow_pct_str = f"({'+' if flow_pct >= 0 else ''}{format_pct(flow_pct)})"
        
        ret_str = f"{'+' if p_ret >= 0 else ''}{format_pct(p_ret, 4)}"
        ret_class = "trend-up" if p_ret >= 0 else "trend-down"
        
        inv_str = f"{inv_change:+d} Kişi"
        inv_class = "trend-up" if inv_change >= 0 else "trend-down"
        inv_pct_str = f"({'+' if inv_pct >= 0 else ''}{format_pct(inv_pct)})"
        
        size_str = '₺' + f"{total_size:,.0f}".replace(",", ".")
        
        html += f"""
        <div class="tracked-card">
            <div class="t-header">
                <span class="t-code">{code}</span>
                <span class="t-price">Fiyat: {price_str}</span>
            </div>
            <div class="t-stats-grid">
                <div class="t-stat-block">
                    <span class="t-label">{period_label} Giriş</span>
                    <span class="t-val-main {flow_class}">{flow_str}</span>
                    <span class="t-val-sub {flow_class}">{flow_pct_str}</span>
                </div>
                <div class="t-stat-block">
                    <span class="t-label">{period_label} Getiri</span>
                    <span class="t-val-main {ret_class}">{ret_str}</span>
                </div>
                <div class="t-stat-block">
                    <span class="t-label">Yeni Kişi ({period_label})</span>
                    <span class="t-val-main {inv_class}">{inv_str}</span>
                    <span class="t-val-sub {inv_class}">{inv_pct_str}</span>
                </div>
                <div class="t-stat-block">
                    <span class="t-label">Toplam Büyüklük</span>
                    <span class="t-val-main">{size_str}</span>
                </div>
            </div>
        </div>
        """
        
    return html

async def main():
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, "data.json")
    config_path = os.path.join(base_dir, "runtime_config.json")
    template_path = os.path.join(base_dir, "template", "index.html")
    output_html_path = os.path.join(base_dir, "template", "filled_index.html")
    output_img_path = os.path.join(base_dir, "infographic.png")
    
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    config = {
        "bg_url": "", 
        "sections": ["inflows", "outflows", "cat_in", "cat_out", "tracked"],
        "grid_cols": 2,
        "tracked_grid_cols": 1,
        "watermark_anchor": "bottom",
        "positions": {
            "inflows": "1,1",
            "outflows": "1,2",
            "cat_in": "2,1",
            "cat_out": "2,2",
            "tracked": "3,1",
            "predictions": "4,1"
        },
        "predictions": []
    }
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
    date_str = data['date']
    period_type = data.get('period_type', 'daily')
    
    if period_type == "daily":
        title = "GÜNLÜK TEFAS ÖZETİ"
        period_label = "Günlük"
        period_note = "(Düne Göre)"
    elif period_type == "weekly":
        title = "HAFTALIK TEFAS ÖZETİ"
        period_label = "Haftalık"
        period_note = "(Geçen Haftaya Göre)"
    else:
        title = "AYLIK TEFAS ÖZETİ"
        period_label = "Aylık"
        period_note = "(Geçen Aya Göre)"
    
    # Generate HTML content based on enabled sections
    sections = config.get("sections", [])
    
    sort_mode = data.get('sort_mode', 'tl')
    
    inflows_html = generate_fund_list_html(data.get('top_inflows', []), True, sort_mode) if "inflows" in sections else ""
    outflows_html = generate_fund_list_html(data.get('top_outflows', []), False, sort_mode) if "outflows" in sections else ""
    
    cat_in_html = generate_fund_list_html(data.get('top_cat_in', []), True, sort_mode) if "cat_in" in sections else ""
    cat_out_html = generate_fund_list_html(data.get('top_cat_out', []), False, sort_mode) if "cat_out" in sections else ""
    
    inv_in_html = generate_investor_list_html(data.get('top_inv_in', [])) if "inv_in" in sections else ""
    inv_out_html = generate_investor_list_html(data.get('top_inv_out', [])) if "inv_out" in sections else ""

    tracked_html = generate_tracked_html(data.get('tracked', {}), period_label) if "tracked" in sections else ""
    
    portfolio_diff_html = generate_portfolio_diff_html(data.get('allocation_diffs', {}), config) if "portfolio_diff" in sections else ""
    
    predictions = config.get("predictions", [])
    predictions_html = generate_predictions_html(predictions) if "predictions" in sections else ""
    
    bg_url = config.get("bg_url", "")
    if not bg_url:
        bg_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2564&auto=format&fit=crop"
    
    print(f"DEBUG: Generating image with sections: {sections}")
    print(f"DEBUG: Background URL: {bg_url}")

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()
        
    template = template.replace("{{TITLE}}", config.get("main_title") if config.get("main_title") else title)
    template = template.replace("{{SUBTITLE}}", config.get("subtitle") if config.get("subtitle") else "Paranın Yönü Nereye?")
    template = template.replace("{{DATE}}", format_turkish_date(date_str))
    template = template.replace("{{PERIOD_NOTE}}", period_note)
    template = template.replace("({{PERIOD_TYPE_LABEL}})", f"({period_label})")
    
    # Header Visibility
    show_main = config.get("header_show_main", True)
    show_sub = config.get("header_show_sub", True)
    template = template.replace("{{SHOW_MAIN}}", "" if show_main else "hidden")
    template = template.replace("{{SHOW_SUB}}", "" if show_sub else "hidden")
    template = template.replace("{{TOP_INFLOWS_HTML}}", inflows_html)
    template = template.replace("{{TOP_OUTFLOWS_HTML}}", outflows_html)
    template = template.replace("{{TOP_CAT_IN_HTML}}", cat_in_html)
    template = template.replace("{{TOP_CAT_OUT_HTML}}", cat_out_html)
    template = template.replace("{{TOP_INV_IN_HTML}}", inv_in_html)
    template = template.replace("{{TOP_INV_OUT_HTML}}", inv_out_html)
    template = template.replace("{{TRACKED_FUNDS_HTML}}", tracked_html)
    template = template.replace("{{PORTFOLIO_DIFF_HTML}}", portfolio_diff_html)
    template = template.replace("{{PREDICTIONS_HTML}}", predictions_html)
    template = template.replace("{{PRED_TITLE}}", config.get("pred_title", "Getiri Tahmini"))
    
    # Handle layout mode class
    if len(sections) == 1 and "predictions" in sections:
        layout_mode_class = "pred-only-layout"
    elif len(sections) == 1 and "portfolio_diff" in sections:
        layout_mode_class = "portfolio-only-layout"
        # Override title to be dynamic for portfolio diff
        diffs = data.get('allocation_diffs', {})
        if diffs:
            target_fund = config.get("portfolio_diff_fund", "PHE").upper()
            if target_fund not in diffs:
                target_fund = list(diffs.keys())[0] if diffs else ""
            template = template.replace(config.get("main_title") if config.get("main_title") else title, f"{target_fund} Portföy Dağılımı")
    else:
        layout_mode_class = "normal-layout"
    template = template.replace("{{LAYOUT_MODE_CLASS}}", layout_mode_class)
    
    # Conditional Visibility and Positioning
    for s_name in ["inflows", "outflows", "cat_in", "cat_out", "inv_in", "inv_out", "tracked", "predictions", "portfolio_diff"]:
        placeholder_show = f"{{{{SHOW_{s_name.upper()}}}}}"
        placeholder_pos = f"/* POS_{s_name.upper()} */"
        
        is_enabled = s_name in sections
        template = template.replace(placeholder_show, "" if is_enabled else "hidden")
        
        # Aggressive hiding via inline style if disabled
        if not is_enabled:
            template = template.replace(placeholder_pos, "display: none !important;")
        else:
            # If enabled, handle positioning for normal mode
            pos_val = config.get("positions", {}).get(s_name, "")
            if pos_val and "," in pos_val:
                row, col = pos_val.split(",")
                template = template.replace(placeholder_pos, f"grid-row: {row}; grid-column: {col};")
            else:
                template = template.replace(placeholder_pos, "")

    # Hide footer if ONLY predictions are shown
    show_footer = "hidden" if len(sections) == 1 and "predictions" in sections else ""
    if show_footer:
        template = template.replace("{{SHOW_FOOTER}}", "hidden")
        # Also hide via inline if possible or just rely on class
    else:
        template = template.replace("{{SHOW_FOOTER}}", "")
    
    # Twitter Hashtags Generation
    all_fund_codes = set()
    for f in data.get('top_inflows', []): all_fund_codes.add(f['fund_code'])
    for f in data.get('top_outflows', []): all_fund_codes.add(f['fund_code'])
    for code in data.get('tracked', {}).keys(): all_fund_codes.add(code)
    hashtags = " ".join([f"#{c}" for c in sorted(list(all_fund_codes))[:10]])
    template = template.replace("{{HASHTAGS}}", hashtags)
    
    # Final cleanup substitutions
    template = template.replace("{{BG_URL}}", bg_url)
    template = template.replace("{{GRID_COLS}}", str(config.get("grid_cols", 2)))
    template = template.replace("{{FOOTER_NOTE}}", "* Veriler TEFAS üzerinden alınmıştır. Serbest (Para Piyasası), Serbest (Kısa Vadeli), Serbest (Katılım), Serbest (Döviz), Para Piyasası kategorileri hariç tutulmuştur.")
    
    # Positions and Dynamic Grid Styles
    positions = config.get("positions", {})
    grid_cols = config.get("grid_cols", 2)
    template = template.replace("/* DYNAMIC_GRID_STYLE */", f"grid-template-columns: repeat({grid_cols}, 1fr); gap: 30px;")
    
    tracked_grid_cols = config.get("tracked_grid_cols", 1)
    tracked_grid_style = f"display: grid; grid-template-columns: repeat({tracked_grid_cols}, 1fr); gap: 25px;"
    template = template.replace("/* DYNAMIC_TRACKED_GRID */", tracked_grid_style)

    # Font size replacements — inject as a <style> block to avoid IDE placeholder corruption
    item_font_size = config.get("item_font_size", 32)
    period_font_size = config.get("period_font_size", 22)
    font_style_injection = f"""<style>
:root {{
    --item-font-size: {item_font_size}px;
    --period-font-size: {period_font_size}px;
}}
</style>"""
    template = template.replace("</head>", font_style_injection + "\n</head>")
    # Also do string replace as fallback in case placeholders survived
    template = template.replace("{{ITEM_FONT_SIZE}}", str(item_font_size))
    template = template.replace("{{PERIOD_FONT_SIZE}}", str(period_font_size))
    
    # Helper to parse "r,c" and generate grid styles
    def get_grid_pos(name):
        pos = positions.get(name, "")
        if not pos or "," not in pos: return ""
        r, c = pos.split(",")
        return f"grid-row: {r}; grid-column: {c};"

    template = template.replace("/* POS_INFLOWS */", get_grid_pos("inflows"))
    template = template.replace("/* POS_OUTFLOWS */", get_grid_pos("outflows"))
    template = template.replace("/* POS_CAT_IN */", get_grid_pos("cat_in"))
    template = template.replace("/* POS_CAT_OUT */", get_grid_pos("cat_out"))
    template = template.replace("/* POS_INV_IN */", get_grid_pos("inv_in"))
    template = template.replace("/* POS_INV_OUT */", get_grid_pos("inv_out"))
    template = template.replace("/* POS_TRACKED */", get_grid_pos("tracked"))
    template = template.replace("/* POS_PREDICTIONS */", get_grid_pos("predictions"))
    template = template.replace("/* POS_PORTFOLIO_DIFF */", get_grid_pos("portfolio_diff"))
    
    # Watermark position is now handled relatively in index.html
    # We clear the placeholder to avoid CSS errors
    template = template.replace("/* POS_WATERMARK */", "")

    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(template)
        
    # Launch Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # Set canvas width to 1080 for Twitter 4:5 Native Portrait
        c_width = config.get("canvas_width", 1080)
        # device_scale_factor=2 applies retina (2160x2700 max physical output)
        page = await browser.new_page(viewport={"width": c_width, "height": 1350}, device_scale_factor=2)
        
        await page.goto(f"file:///{output_html_path}")
        
        # Wait for background image and other resources to load
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except:
            print("Warning: Network idle timeout reached. Proceeding with screenshot.")
        
        # Adjust height according to content
        await page.wait_for_selector(".infographic-container")
        container = await page.query_selector(".infographic-container")
        box = await container.bounding_box()
        if box:
            await page.set_viewport_size({"width": c_width, "height": int(box['height'])})
        
        await page.screenshot(path=output_img_path)
        await browser.close()
    
    print(f"Generated successfully: {output_img_path}")

if __name__ == "__main__":
    asyncio.run(main())
