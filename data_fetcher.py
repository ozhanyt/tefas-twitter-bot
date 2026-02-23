import sys
import os
import json
import logging
import time
from datetime import datetime, timedelta
import concurrent.futures
import argparse

sys.path.append(r"C:\Users\svkto\.gemini\antigravity\scratch\borsapy_repo")
import borsapy as bp
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_prev_row(df, period_type):
    latest_date = df.index[-1]
    if period_type == "daily":
        return df.iloc[-2] if len(df) > 1 else df.iloc[0]
    elif period_type == "weekly":
        target = latest_date - timedelta(days=7)
    elif period_type == "monthly":
        target = latest_date - timedelta(days=30)
    else:
        return df.iloc[-2]
        
    past_df = df[df.index <= target]
    return past_df.iloc[-1] if not past_df.empty else df.iloc[0]

def get_fund_flow(fund_code, period_type):
    try:
        fund = bp.Fund(fund_code)
        # Fetching 3 months of data to safely get 30-day lookback for 'monthly'
        df = fund.history(period="3mo")
        if df.empty or len(df) < 2:
            return None
            
        shares_col = 'Shares' if 'Shares' in df.columns else 'Tedavüldeki Pay Sayısı' if 'Tedavüldeki Pay Sayısı' in df.columns else None
        if shares_col is None:
            df['Shares'] = df['FundSize'] / df['Price']
            shares_col = 'Shares'
            
        latest = df.iloc[-1]
        prev = get_prev_row(df, period_type)
        
        latest_shares = latest[shares_col]
        prev_shares = prev[shares_col]
        
        # Inflow/Outflow calculation
        net_flow = (latest_shares - prev_shares) * latest['Price']
        flow_pct = (net_flow / prev['FundSize']) * 100 if prev['FundSize'] > 0 else 0
        
        # Investor change
        inv_latest = latest.get('Investors', 0)
        inv_prev = prev.get('Investors', 0)
        inv_change = inv_latest - inv_prev
        inv_change_pct = (inv_change / inv_prev * 100) if inv_prev > 0 else 0
        
        return {
            'fund_code': fund_code,
            'name': fund.info.get('name', ''),
            'net_flow': float(net_flow),
            'fund_size': float(latest['FundSize']),
            'flow_pct': float(flow_pct),
            'investors': int(inv_latest),
            'inv_change': int(inv_change),
            'inv_change_pct': float(inv_change_pct)
        }
    except Exception as e:
        logging.error(f"Error fetching fund {fund_code}: {e}")
        return None

def normalize(s):
    if not s: return ""
    s = str(s).lower()
    repls = {'ı': 'i', 'ş': 's', 'ğ': 'g', 'ü': 'u', 'ö': 'o', 'ç': 'c', 'i̇': 'i'}
    for k, v in repls.items():
        s = s.replace(k, v)
    return s

def fetch_all_flows(period_type, selected_cats=None, sort_mode='tl'):
    logging.info(f"Screening funds for {period_type} period (Sort: {sort_mode})...")
    
    # Mapping of categories to keywords for granular filtering
    # Keys here MUST match the dashboard checkbox values exactly
    cat_to_keywords = {
        "Hisse Senedi": ["Hisse Senedi", "Hisse"],
        "Değişken": ["Değişken", "Degisken"],
        "Karma": ["Karma"],
        "Fon Sepeti": ["Fon Sepeti"],
        "Borçlanma Araçları": ["Borçlanma Araçları", "Borclanma Aracları", "Tahvil", "Bono"],
        "K.Maden": ["Altın", "Gümüş", "Kıymetli Maden", "Altin", "Gumus"],  # dashboard sends 'K.Maden'
        "Katılım": ["Katılım", "Katilim"],
        "Para Piy.": ["Para Piyasası", "Para Piyasasi"],  # dashboard sends 'Para Piy.'
        "Serbest (Genel)": ["Serbest"],        # dashboard sends 'Serbest (Genel)'
        "Serbest (P.Piy)": ["Serbest", "Para Piyasası"],  # dashboard sends 'Serbest (P.Piy)'
        "Serbest (Döviz)": ["Serbest", "Döviz"],
        "Serbest (K.Vade)": ["Serbest", "Kısa Vadeli"],  # dashboard sends 'Serbest (K.Vade)'
        "Serbest (Katılım)": ["Serbest", "Katılım"]
    }
    
    all_cats = sorted(cat_to_keywords.keys(), key=len, reverse=True)
    df_yat = bp.screen_funds(fund_type="YAT", limit=5000)
    df_yat = pd.DataFrame(df_yat)
    fund_codes_all = df_yat['fund_code'].tolist()
    code_to_type = dict(zip(df_yat['fund_code'], df_yat['fund_type']))
    
    results_all = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_code = {executor.submit(get_fund_flow, code, period_type): code for code in fund_codes_all}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_code)):
            try:
                res = future.result()
                if res: results_all.append(res)
                time.sleep(0.05)
            except: pass
            if (i+1) % 100 == 0: logging.info(f"Processed {i+1}/{len(fund_codes_all)} funds...")
                
    # Filter for Leaders
    results_filtered = []
    if selected_cats:
        for r in results_all:
            ftype = str(code_to_type.get(r['fund_code'], ''))
            fname_n = normalize(r['name'])
            effective_cat = ""
            if "Serbest" in ftype:
                # Map to dashboard checkbox values
                if any(x in fname_n for x in ["para piyasasi", "p.piy"]): effective_cat = "Serbest (P.Piy)"
                elif any(x in fname_n for x in ["doviz", "yabanci", "eurobond"]): effective_cat = "Serbest (Döviz)"
                elif any(x in fname_n for x in ["kisa vadeli", "k.vade"]): effective_cat = "Serbest (K.Vade)"
                elif "katilim" in fname_n: effective_cat = "Serbest (Katılım)"
                else: effective_cat = "Serbest (Genel)"  # FIX: was 'Serbest', dashboard sends 'Serbest (Genel)'
            elif any(x in ftype for x in ["Kıymetli Maden", "Altın", "Gümüş"]):
                effective_cat = "K.Maden"  # FIX: was 'Kıymetli Madenler', dashboard sends 'K.Maden'
            elif "Para Piyasası" in ftype:
                effective_cat = "Para Piy."  # FIX: was 'Para Piyasası', dashboard sends 'Para Piy.'
            else:
                for cat_name in all_cats:
                    if cat_name in ftype:
                        effective_cat = cat_name
                        break
            if effective_cat in selected_cats: results_filtered.append(r)
    else:
        results_filtered = [r for r in results_all if not any(x in normalize(r['name']) for x in ["para piyasasi", "p.piy", "doviz", "yabanci"])]
    
    # Investor Count Filter: Exclude funds with fewer than 500 investors from Leaderboards
    # These are usually closed/institutional funds not available for general TEFAS trading
    results_filtered = [r for r in results_filtered if r.get('investors', 0) >= 500]
    
    # SORT LEADERS
    sort_key = 'net_flow' if sort_mode == 'tl' else 'flow_pct'
    
    # Filter for positive and negative flows separately
    inflows_only = [r for r in results_filtered if r[sort_key] > 0]
    outflows_only = [r for r in results_filtered if r[sort_key] < 0]
    
    inflows_only.sort(key=lambda x: x[sort_key], reverse=True)
    outflows_only.sort(key=lambda x: x[sort_key], reverse=False) # Most negative first
    
    top_inflows = inflows_only[:5]
    top_outflows = outflows_only[:5]
    
    # INVESTOR LEADERS
    # Filter for positive changes for 'in' and negative for 'out'
    inv_pos = [r for r in results_all if r['inv_change'] > 0 and not any(x in normalize(r['name']) for x in ["para piyasasi", "p.piy"])]
    inv_neg = [r for r in results_all if r['inv_change'] < 0 and not any(x in normalize(r['name']) for x in ["para piyasasi", "p.piy"])]
    
    inv_pos.sort(key=lambda x: x['inv_change'], reverse=True)
    inv_neg.sort(key=lambda x: x['inv_change'], reverse=False)
    
    top_inv_in = inv_pos[:5]
    top_inv_out = inv_neg[:5]

    # Category flows
    cat_flows = {}
    for res in results_all:
        code = res['fund_code']
        ftype = code_to_type.get(code, 'Diğer').replace("Şemsiye Fonu", "").strip()
        if ftype not in cat_flows:
            cat_flows[ftype] = {'fund_code': ftype, 'name': '', 'net_flow': 0, 'fund_size': 0}
        cat_flows[ftype]['net_flow'] += res.get('net_flow', 0)
        cat_flows[ftype]['fund_size'] += res.get('fund_size', 0)
        
    for k, v in cat_flows.items():
        v['flow_pct'] = (v['net_flow'] / v['fund_size']) * 100 if v['fund_size'] > 0 else 0
        
    cat_list = list(cat_flows.values())
    cat_list_in = sorted([c for c in cat_list if c['net_flow'] > 0], key=lambda x: x['net_flow'], reverse=True)[:5]
    cat_list_out = sorted([c for c in cat_list if c['net_flow'] < 0], key=lambda x: x['net_flow'])[:5]
    
    # Footer
    if selected_cats:
        excl = [cat for cat in all_cats if cat not in selected_cats]
        footer_detail = f"{', '.join(excl)} kategorileri hariç tutulmuştur." if excl else "Tüm ana kategoriler dahil edilmiştir."
    else:
        footer_detail = "Para Piyasası ve Döviz fonları hariç tutulmuştur."
    footer_note = f"* Veriler TEFAS üzerinden alınmıştır. {footer_detail}"
    
    return top_inflows, top_outflows, cat_list_in, cat_list_out, top_inv_in, top_inv_out, footer_note

def fetch_tracked_funds(tracked_codes, period_type):
    tracked_data = {}
    for code in tracked_codes:
        try:
            fund = bp.Fund(code)
            df = fund.history(period="3mo")
            if df.empty or len(df) < 2: continue
            shares_col = 'Shares' if 'Shares' in df.columns else 'Tedavüldeki Pay Sayısı' if 'Tedavüldeki Pay Sayısı' in df.columns else None
            if shares_col is None:
                df['Shares'] = df['FundSize'] / df['Price']
                shares_col = 'Shares'
            latest = df.iloc[-1]
            prev = get_prev_row(df, period_type)
            flow = (latest[shares_col] - prev[shares_col]) * latest['Price']
            flow_pct = (flow / prev['FundSize']) * 100 if prev['FundSize'] > 0 else 0
            inv_change = latest['Investors'] - prev['Investors']
            inv_change_pct = (inv_change / prev['Investors']) * 100 if prev['Investors'] > 0 else 0
            return_pct = ((latest['Price'] - prev['Price']) / prev['Price']) * 100
            tracked_data[code] = {
                'fund_code': code, 'name': fund.info.get('name', ''), 'price': float(latest['Price']),
                'fund_size': float(latest['FundSize']), 'investors': int(latest['Investors']),
                'period_flow': float(flow), 'period_flow_pct': float(flow_pct),
                'period_investor_change': int(inv_change), 'period_investor_pct': float(inv_change_pct),
                'period_return_pct': float(return_pct)
            }
        except: pass
    return tracked_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("period", choices=["daily", "weekly", "monthly"], default="daily", nargs="?")
    parser.add_argument("tracked", default="TLY, DFI, PHE", nargs="?")
    parser.add_argument("cats", default="", nargs="?")
    parser.add_argument("--sort", choices=["tl", "pct"], default="tl")
    args = parser.parse_args()
    
    selected_cats = [c.strip() for c in args.cats.split(",") if c.strip()]
    raw_tracked = args.tracked.split(",")
    tracked_codes = [code.strip().upper() for code in raw_tracked if code.strip()]
    if not tracked_codes: tracked_codes = ['TLY', 'DFI', 'PHE']
        
    tracked_data = fetch_tracked_funds(tracked_codes, args.period)
    top_inflows, top_outflows, top_cat_in, top_cat_out, top_inv_in, top_inv_out, footer_note = fetch_all_flows(args.period, selected_cats, args.sort)
    
    output = {
        'date': datetime.now().strftime("%Y-%m-%d"),
        'period_type': args.period,
        'sort_mode': args.sort,
        'top_inflows': top_inflows,
        'top_outflows': top_outflows,
        'top_cat_in': top_cat_in,
        'top_cat_out': top_cat_out,
        'top_inv_in': top_inv_in,
        'top_inv_out': top_inv_out,
        'tracked': tracked_data,
        'footer_note': footer_note
    }
    
    out_path = os.path.join(os.path.dirname(__file__), "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logging.info(f"Data saved to {out_path}")
