import sys
import os
import pandas as pd
from datetime import datetime

# Add borsapy to path
sys.path.append(r"C:\Users\svkto\.gemini\antigravity\scratch\borsapy_repo")
import borsapy as bp

def get_allocation_diff(fund_code):
    fund = bp.Fund(fund_code)
    try:
        df = fund.allocation_history(period="1mo")
        # Ensure we have date as datetime to sort properly
        df['Date'] = pd.to_datetime(df['Date'])
        # Get unique dates sorted descending
        dates = sorted(df['Date'].unique(), reverse=True)
        
        if len(dates) < 2:
            print(f"Not enough data for {fund_code}")
            return
            
        latest_date = dates[0]
        prev_date = dates[1]
        
        print(f"[{fund_code}] Comparing {latest_date.strftime('%Y-%m-%d')} with {prev_date.strftime('%Y-%m-%d')}")
        
        df_latest = df[df['Date'] == latest_date].copy()
        df_prev = df[df['Date'] == prev_date].copy()
        
        # Merge on asset_name to calculate diff
        merged = pd.merge(df_latest, df_prev, on='asset_name', how='outer', suffixes=('_latest', '_prev'))
        
        # Fill NaNs with 0 for weights
        merged['weight_latest'] = merged['weight_latest'].fillna(0)
        merged['weight_prev'] = merged['weight_prev'].fillna(0)
        
        merged['diff'] = merged['weight_latest'] - merged['weight_prev']
        
        # Sort by latest weight descending
        merged = merged.sort_values(by='weight_latest', ascending=False)
        
        print("\n--- Dağılım ve Değişim ---")
        for _, row in merged.iterrows():
            asset = row['asset_name']
            w_latest = row['weight_latest']
            diff = row['diff']
            
            sign = "+" if diff > 0 else ""
            if w_latest == 0 and diff == 0:
                continue
                
            print(f"{asset}: %{w_latest:.2f} ({sign}%{diff:.2f})")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_allocation_diff("PHE")
