import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime, date
import sys
import os
from dateutil.relativedelta import relativedelta

# Add workspace root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.database.db_helper import run_query, run_command, run_command_batch
from backend.logger import get_logger

logger = get_logger(__name__)

import warnings
warnings.filterwarnings('ignore')

def get_base_data():
    logger.info("Fetching base data...")
    df_sales = run_query("""
        SELECT item_id, date_trunc('month', date) as date, SUM(amount) as actual_requirement
        FROM sales_out_history GROUP BY item_id, date
    """)
    df_sales['date'] = pd.to_datetime(df_sales['date']).dt.tz_localize(None)
    
    df_warehouse = run_query("""
        SELECT item_id, date_trunc('month', date) as date,
        SUM(CASE WHEN target_warehouse LIKE 'HK%' THEN amount ELSE 0 END) - 
        SUM(CASE WHEN source_warehouse LIKE 'HK%' THEN amount ELSE 0 END) as actual_requirement
    FROM warehouse_movements GROUP BY item_id, date
    """)
    if not df_warehouse.empty:
        df_warehouse['date'] = pd.to_datetime(df_warehouse['date']).dt.tz_localize(None)
        df_cons = pd.concat([df_sales, df_warehouse]).groupby(['item_id', 'date'])[['actual_requirement']].sum().reset_index()
    else:
        df_cons = df_sales
    
    df_prophet_hist = run_query("SELECT item_id, date, amount as prophet_forecast FROM prophet_table_history")
    df_prophet_temp = run_query("SELECT item_id, date, amount as prophet_forecast FROM prophet_table_temporary")
    df_prophet = pd.concat([df_prophet_hist, df_prophet_temp])
    df_prophet['date'] = pd.to_datetime(df_prophet['date']).dt.tz_localize(None)

    df_purchase = run_query("SELECT item_id, purchase_date, delay_day, purpose FROM purchase WHERE actual_coming_date IS NOT NULL")
    df_purchase['purchase_date'] = pd.to_datetime(df_purchase['purchase_date']).dt.tz_localize(None)

    df_master = run_query("""
        SELECT i.item_id, i.item_type, i.item_quantity_type, sk.leadtime_avg, sk.leadtime_deviation, sk.result_king
        FROM item i LEFT JOIN ss_kings_formula sk ON i.item_id = sk.item_id
    """)
    return df_cons, df_prophet, df_purchase, df_master

def calculate_rolling_features(df_cons, until_date):
    df_hist = df_cons[df_cons['date'] < until_date].copy()
    if df_hist.empty: return pd.DataFrame(columns=['item_id', 'rolling_cons_6m', 'rolling_cons_12m'])
    df_hist = df_hist.sort_values(['item_id', 'date'])
    results = []
    for item_id, group in df_hist.groupby('item_id'):
        results.append({
            'item_id': item_id,
            'rolling_cons_6m': group['actual_requirement'].tail(6).mean(),
            'rolling_cons_12m': group['actual_requirement'].tail(12).mean()
        })
    return pd.DataFrame(results)

def calculate_risk_features(df_purchase, until_date):
    df_hist = df_purchase[df_purchase['purchase_date'] < until_date].copy()
    if df_hist.empty: return pd.DataFrame(columns=['item_id', 'month', 'max_supplier_delay', 'avg_supplier_delay', 'urgent_order_ratio'])
    df_hist['month'] = df_hist['purchase_date'].dt.month
    risk = df_hist.groupby(['item_id', 'month']).agg(
        max_supplier_delay=('delay_day', 'max'), avg_supplier_delay=('delay_day', 'mean'),
        urgent_count=('purpose', lambda x: (x == 'acil_sipariş').sum()), total_count=('purpose', 'count')
    ).reset_index()
    risk['urgent_order_ratio'] = (risk['urgent_count'] / risk['total_count']).fillna(0)
    return risk[['item_id', 'month', 'max_supplier_delay', 'avg_supplier_delay', 'urgent_order_ratio']]

def main():
    df_cons, df_prophet, df_purchase, df_master = get_base_data()
    run_command("TRUNCATE safety_stock_history")
    
    # Start Date for Backtest
    current_date = pd.to_datetime("2021-01-01")
    end_date = pd.to_datetime("2026-12-01")

    
    
    cat_features = ['item_type', 'item_quantity_type']
    features = ['prophet_forecast', 'leadtime_avg', 'leadtime_deviation', 'result_king', 
                'max_supplier_delay', 'avg_supplier_delay', 'urgent_order_ratio', 
                'month', 'rolling_cons_6m', 'rolling_cons_12m']
    all_features = features + cat_features

    # Training logic: We can train once per year to save time, OR once per month for extreme accuracy.
    # Let's train once per year, but PREDICT and UPDATE FEATURES once per month.
    
    while current_date <= end_date:
        logger.info(f"--- Predicting Month: {current_date.strftime('%Y-%m')} ---")
        
        # 1. Update Features for THIS month based on data before current_date
        df_risk = calculate_risk_features(df_purchase, current_date)
        df_rolling = calculate_rolling_features(df_cons, current_date)
        
        # 2. Prepare Training Set (All data before THIS month)
        df_train = df_cons[df_cons['date'] < current_date].copy()
        if df_train.empty:
            current_date += relativedelta(months=1)
            continue

        df_train['month'] = df_train['date'].dt.month
        df_train = df_train.merge(df_prophet, on=['item_id', 'date'], how='left')
        df_train = df_train.merge(df_master, on='item_id', how='left')
        df_train = df_train.merge(df_risk, on=['item_id', 'month'], how='left')
        df_train = df_train.merge(df_rolling, on='item_id', how='left')
        df_train = df_train.fillna(0)
        for c in cat_features: df_train[c] = df_train[c].astype('category')




        # 3. Model (We use higher n_estimators for lower learning rate)
        model = lgb.LGBMRegressor(
            objective='quantile', alpha=0.85,
            n_estimators=3000, learning_rate=0.03, num_leaves=31,
            verbose=-1, random_state=42
        )
        #döndür değiştirebilsinler





        model.fit(df_train[all_features], df_train['actual_requirement'])

        # 4. Predict THIS month
        active_items = set(df_cons[df_cons['date'] < current_date]['item_id'].unique()) | \
                       set(df_prophet[df_prophet['date'] == current_date]['item_id'].unique())
        items = [i for i in df_master['item_id'].unique() if i in active_items]
        
        df_predict = pd.DataFrame({'item_id': items, 'date': current_date})
        df_predict['month'] = current_date.month
        df_predict = df_predict.merge(df_prophet, on=['item_id', 'date'], how='left')
        df_predict = df_predict.merge(df_master, on='item_id', how='left')
        df_predict = df_predict.merge(df_risk, on=['item_id', 'month'], how='left')
        df_predict = df_predict.merge(df_rolling, on='item_id', how='left')
        df_predict = df_predict.fillna(0)
        for c in cat_features: df_predict[c] = df_predict[c].astype('category')

        preds = model.predict(df_predict[all_features])
        df_predict['safety_amount'] = np.maximum(preds, 0)
        df_predict.loc[(df_predict['prophet_forecast'] == 0) & (df_predict['rolling_cons_12m'] == 0), 'safety_amount'] = 0

        # 5. Save
        batch_data = [(row['item_id'], row['date'].date(), round(float(row['safety_amount']), 5)) for _, row in df_predict.iterrows()]
        run_command_batch("INSERT INTO safety_stock_history (item_id, date, safety_amount) VALUES (%s, %s, %s) ON CONFLICT (item_id, date) DO UPDATE SET safety_amount = EXCLUDED.safety_amount;", batch_data)
        
        current_date += relativedelta(months=1)

    logger.info("Monthly recursive backtest completed!")

if __name__ == "__main__":
    main()
