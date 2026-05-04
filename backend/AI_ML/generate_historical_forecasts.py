import pandas as pd
from prophet import Prophet
import logging
from datetime import datetime
from backend.database.db_helper import run_query, run_command_batch, run_command
from backend.logger import get_logger

logger = get_logger(__name__)
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
logging.getLogger('prophet').setLevel(logging.WARNING)

def run_historical_step(item_id, target_year):
    """
    Belirli bir yil icin (hedef yil), o yildan onceki verileri kullanarak tahmin uretir.
    """
    # Hedef yildan onceki tum verileri cek
    query = """
    SELECT date_trunc('month', date) as ds, SUM(amount) as y 
    FROM sales_out_history 
    WHERE item_id = %s AND date < %s
    GROUP BY date_trunc('month', date)
    ORDER BY ds
    """
    cutoff_date = f"{target_year}-01-01"
    df = run_query(query, (item_id, cutoff_date))
    
    if df.empty or len(df) < 5: 
        return []

    df['ds'] = pd.to_datetime(df['ds']).dt.tz_localize(None)

    try:
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.01 
        )
        model.fit(df)
        
        # Sadece o hedef yil icin 12 aylik periyot olustur
        start_date = datetime(target_year, 1, 1)
        future_dates = pd.date_range(start=start_date, periods=12, freq='MS')
        future = pd.DataFrame({'ds': future_dates})
        
        forecast = model.predict(future)
        
        results = []
        for _, row in forecast.iterrows():
            pred_value = max(0, row['yhat'])
            lower = max(0, row['yhat_lower'])
            upper = max(0, row['yhat_upper'])
            results.append((item_id, row['ds'].date(), round(pred_value, 5), round(lower, 5), round(upper, 5), True)) # is_approved=True
            
        return results

    except Exception as e:
        logger.error(f"Error forecasting {item_id} for year {target_year}: {e}")
        return []

def generate_all_history():
    # 0. Mevcut gecmisi temizle
    print("Clearing existing historical forecasts...")
    run_command("TRUNCATE TABLE prophet_table_history")

    # 1. Tum urunleri al
    items_df = run_query("SELECT DISTINCT item_id FROM sales_out_history")
    items = items_df['item_id'].tolist()
    
    years = [2021, 2022, 2023, 2024, 2025, 2026]
    
    print(f"Starting historical forecast generation for {len(items)} items over years {years}...")
    
    all_results = []
    
    for year in years:
        print(f"\n>>> Processing Year: {year}")
        for idx, item_id in enumerate(items):
            res = run_historical_step(item_id, year)
            if res:
                all_results.extend(res)
            
            if (idx + 1) % 20 == 0:
                print(f"  Processed {idx + 1}/{len(items)} items for {year}...")

    if not all_results:
        print("No forecasts generated.")
        return

    print(f"\nFinalizing... Total monthly forecast records generated: {len(all_results)}")
    
    # 2. History tablosuna kaydet
    insert_query = """
    INSERT INTO prophet_table_history (item_id, date, amount, yhat_lower, yhat_upper, is_approved)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (item_id, date) DO UPDATE SET 
        amount = EXCLUDED.amount,
        yhat_lower = EXCLUDED.yhat_lower,
        yhat_upper = EXCLUDED.yhat_upper,
        is_approved = TRUE
    """
    
    print("Writing to database (prophet_table_history)...")
    if run_command_batch(insert_query, all_results):
        print("SUCCESS! All historical forecasts have been saved.")
    else:
        print("FAILED to write to database.")

if __name__ == "__main__":
    generate_all_history()
