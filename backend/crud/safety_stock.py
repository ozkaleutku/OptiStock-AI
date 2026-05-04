import pandas as pd
from backend.database.db_helper import run_query, run_command, run_command_batch
from backend.AI_ML import lightgbm_algo as lightgbm
from backend.crud import bom_explosion
from backend.logger import get_logger

logger = get_logger(__name__)

def calculate_safety_stock():
    logger.info("Safety Stock Calculation Orchestrator Started...")

    # 2. Run LightGBM Training & Prediction
    # This script will update safety_stock_plan with new predictions
    logger.info(">>> Triggering LightGBM...")
    lightgbm.run_lightgbm_training()

    # 3. Run BOM Explosion
    # This script propagates mamül forecasts down to components in safety_stock_plan
    logger.info(">>> Triggering BOM Explosion...")
    bom_explosion.run_bom_explosion()

    logger.info("Safety Stock Calculation Full Cycle Completed.")

def approve_safety_stock_plan(approval_list):
    """
    Safety Stock önerilerini 'safety_stock_plan' tablosunda onaylar.
    
    approval_list: List of dicts or objects with (item_id, date, amount, item_quantity_type)
    """
    from datetime import date
    
    # 2. Batch Upsert (ON CONFLICT)
    sql_upsert = """
    INSERT INTO safety_stock_plan (item_id, date, manual_amount, preference, item_quantity_type, is_approved)
    VALUES (%s, %s, %s, %s, %s, TRUE)
    ON CONFLICT (item_id, date) 
    DO UPDATE SET 
        manual_amount = EXCLUDED.manual_amount, 
        preference = EXCLUDED.preference, 
        item_quantity_type = EXCLUDED.item_quantity_type, 
        is_approved = TRUE
    """
    
    batch_data = [
        (item.item_id, item.date, item.amount if item.preference == 'Manual' else None, item.preference, item.item_quantity_type)
        for item in approval_list
    ]
    
    if batch_data:
        run_command_batch(sql_upsert, batch_data)
        
    return len(batch_data)
        
    return len(batch_data)

def get_final_safety_stock(from_date):
    """Onaylanmış emniyet stoklarını getirir."""
    sql = """
    SELECT 
        item_id, 
        date, 
        CASE 
            WHEN preference = 'Manual' THEN manual_amount
            WHEN preference = 'Formula' THEN formula_amount
            ELSE ai_amount
        END as safety_stock, 
        item_quantity_type
    FROM safety_stock_plan
    WHERE date >= %s AND is_approved = TRUE AND item_type = 'hammadde'
    ORDER BY date, item_id
    """
    return run_query(sql, (from_date,))

def get_calculated_safety_stock_temp():
    """Onay bekleyen (gelecek) planları çeker."""
    sql = """
    SELECT 
        item_id, 
        date, 
        ai_amount,
        formula_amount,
        manual_amount,
        preference,
        is_approved,
        item_type, 
        item_quantity_type
    FROM safety_stock_plan 
    WHERE item_type = 'hammadde' 
      AND date >= DATE_TRUNC('month', CURRENT_DATE)::DATE
    ORDER BY date, item_id
    """
    return run_query(sql)

def get_kings_formula_results():
    """King's Formula sonuçlarını çeker"""
    sql = """
    SELECT item_id, MAX(result_king) as formula_result 
    FROM ss_kings_formula 
    GROUP BY item_id
    """
    return run_query(sql)

def get_all_active_safety_stock():
    """Tüm aktif onaylanmış safety stock değerlerini çeker"""
    sql = """
    SELECT item_id, date::text as active_date, COALESCE(manual_amount, ai_amount) as active_safety_stock 
    FROM safety_stock_plan 
    WHERE is_approved = TRUE
    """
    return run_query(sql)

