import pandas as pd
from prophet import Prophet
import logging
from datetime import datetime

from backend.database.db_helper import run_query, run_command, run_command_batch
from backend.logger import get_logger

logger = get_logger(__name__)

# Prophet loglarını temizlemek için
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
logging.getLogger('prophet').setLevel(logging.WARNING)

def run_prophet_by_item(item_id, target_year):
    # 1. Pull data (monthly total)
    query = """
    SELECT date_trunc('month', date) as ds, SUM(amount) as y 
    FROM sales_out_history 
    WHERE item_id = %s 
    GROUP BY date_trunc('month', date)
    ORDER BY ds
    """
    df = run_query(query, (item_id,))
    
    if df.empty or len(df) < 5: 
        logger.warning(f"Skipping {item_id}: Insufficient data ({len(df)} records)")
        return []

    # convert date to datetime format (remove timezone info - Prophet needs timezone-naive)
    df['ds'] = pd.to_datetime(df['ds']).dt.tz_localize(None)

    try:


        # 2. Train model you can change paremeters if you want
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.01 
        )




        model.fit(df)
        
        # 3. Create future year's calendar
        start_date = datetime(target_year, 1, 1)
        future_dates = pd.date_range(start=start_date, periods=12, freq='MS')
        future = pd.DataFrame({'ds': future_dates})
        
        # 4. Make forecast
        forecast = model.predict(future)
        
        # 5. Prepare Results (with yhat_lower and yhat_upper)
        results = []
        for _, row in forecast.iterrows():
            pred_value = max(0, row['yhat'])
            lower = max(0, row['yhat_lower'])
            upper = max(0, row['yhat_upper'])
            results.append((item_id, row['ds'].date(), round(pred_value, 5), round(lower, 5), round(upper, 5)))
            
        return results

    except Exception as e:
        logger.error(f"Error forecasting {item_id}: {e}")
        return []

def run_full_analysis():
    """
    Sistemdeki tüm ürünler için tahmini çalıştırır ve veritabanına yazar.
    """
    logger.info("Prophet Analysis Started...")
    
    # next year: 
    target_year = datetime.now().year + 1
    logger.info(f"Target Year: {target_year}")

    # 1. Get unique items
    items_df = run_query("SELECT DISTINCT item_id FROM sales_out_history")
    items = items_df['item_id'].tolist()
    
    if not items:
        logger.warning("Analiz edilecek geçmiş veri bulunamadı.")
        return

    # 2. Forecast per item (in memory)
    logger.info("Tahminler hesaplanıyor...")
    all_forecasts = []
    for item_id in items:
        forecasts = run_prophet_by_item(item_id, target_year)
        if forecasts:
            all_forecasts.extend(forecasts)
    
    if not all_forecasts:
        logger.warning("Tahmin üretilemedi.")
        return

    logger.info(f"Toplam {len(all_forecasts)} aylık tahmin üretildi. Veritabanı güncelleniyor...")

    # 3. Database Operations (Transaction like security)
    # A. Backup current data to history table
    logger.info("Backing up current temporary data to history table...")
    run_command("""
    INSERT INTO prophet_table_history (item_id, date, amount, yhat_lower, yhat_upper)
    SELECT item_id, date, amount, yhat_lower, yhat_upper FROM prophet_table_temporary
    ON CONFLICT (item_id, date) DO NOTHING
    """)

    # B. Clear Temporary Table
    logger.info("Clearing temporary table...")
    run_command("TRUNCATE TABLE prophet_table_temporary")

    # C. Save New Data
    logger.info("Saving new forecasts...")
    insert_query = """
    INSERT INTO prophet_table_temporary (item_id, date, amount, yhat_lower, yhat_upper)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (item_id, date) DO UPDATE SET amount = EXCLUDED.amount,
        yhat_lower = EXCLUDED.yhat_lower, yhat_upper = EXCLUDED.yhat_upper
    """
    if run_command_batch(insert_query, all_forecasts):
        logger.info("Kayıt başarılı.")
    else:
        logger.error("Kayıt sırasında hata oluştu!")

    logger.info(f"Analiz Tamamlandı.")

if __name__ == "__main__":
    run_full_analysis()
