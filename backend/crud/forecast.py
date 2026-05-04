from backend.database.db_helper import run_query, run_command

def get_forecast_data():
    """Prophet tahmin verilerini getirir (Gelecek aylar)."""
    sql = """
    SELECT p.*, i.item_quantity_type 
    FROM prophet_table_temporary p
    LEFT JOIN item i ON p.item_id = i.item_id
    WHERE p.date >= DATE_TRUNC('month', CURRENT_DATE)::DATE
    AND p.item_id IN (SELECT DISTINCT item_id FROM sales_out_history)
    ORDER BY p.is_approved ASC, p.date ASC
    """
    return run_query(sql)

def update_forecast_data(item_id, date, amount):
    """Prophet tahmin verisini günceller."""
    sql = """
    UPDATE prophet_table_temporary 
    SET amount = %s, is_approved = FALSE
    WHERE item_id = %s AND date = %s
    """
    return run_command(sql, (amount, item_id, date))

def approve_forecast():
    """Tüm tahmin verilerini onaylar."""
    sql = "UPDATE prophet_table_temporary SET is_approved = TRUE WHERE date >= CURRENT_DATE"
    return run_command(sql)

def approve_forecast_row(item_id, date):
    """Tek bir satırı onaylar."""
    sql = "UPDATE prophet_table_temporary SET is_approved = TRUE WHERE item_id = %s AND date = %s"
    return run_command(sql, (item_id, date))

def get_historical_sales(item_id, target_month):
    """
    Belirli bir ürün ve ayın son 4 yıllık satış geçmişini getirir.
    """
    sql = """
    SELECT 
        EXTRACT(YEAR FROM date) as year,
        SUM(amount) as total_sales
    FROM sales_out_history
    WHERE item_id = %s 
    AND EXTRACT(MONTH FROM date) = %s
    AND date >= CURRENT_DATE - INTERVAL '4 years'
    GROUP BY EXTRACT(YEAR FROM date)
    ORDER BY year DESC
    LIMIT 4
    """
    return run_query(sql, (item_id, target_month))

def get_forecast_detail(item_id):
    """
    Yeni DemandForecast sayfası için birleştirilmiş detay verisi döner.
    Sales History (Tüm aylar) + Prophet Tahminleri (Geçici + Geçmiş).
    """
    # 1. Satış Geçmişi (Aylık Toplam)
    history_sql = """
    SELECT 
        EXTRACT(YEAR FROM date)::INT as year,
        EXTRACT(MONTH FROM date)::INT as month,
        SUM(amount) as total_sales
    FROM sales_out_history
    WHERE item_id = %s
    AND date >= DATE_TRUNC('year', CURRENT_DATE) - INTERVAL '4 years'
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
    df_history = run_query(history_sql, (item_id,))
    
    # 2. Prophet Tahminleri (Temporary + History tablosundan)
    forecast_sql = """
    SELECT date::TEXT as date, amount as yhat, yhat_lower, yhat_upper, is_approved
    FROM prophet_table_temporary
    WHERE item_id = %s
    UNION ALL
    SELECT date::TEXT as date, amount as yhat, yhat_lower, yhat_upper, is_approved
    FROM prophet_table_history
    WHERE item_id = %s
    ORDER BY date
    """
    df_forecast = run_query(forecast_sql, (item_id, item_id))
    
    return {
        "sales_history": df_history.to_dict(orient="records") if not df_history.empty else [],
        "forecast": df_forecast.to_dict(orient="records") if not df_forecast.empty else []
    }
