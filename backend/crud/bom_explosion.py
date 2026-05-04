import pandas as pd
from backend.database.db_helper import run_query, run_command, run_command_batch
from backend.logger import get_logger

logger = get_logger(__name__)

def run_bom_explosion():
    logger.info("BOM Tablosu Parcalaniyor ve Full Safety Stock Hesaplaniyor...")

    # 1. Fetch existing L0 (Mamül) AI plans from safety_stock_plan
    # We only explode non-approved plans to avoid overwriting final decisions
    query_l0 = """
    SELECT item_id, date, ai_amount as amount 
    FROM safety_stock_plan 
    WHERE item_type = 'mamül' AND is_approved = FALSE
    """
    df_current = run_query(query_l0)
    
    if df_current.empty:
        logger.info("Explosion için Mamül seviyesinde AI verisi bulunamadı.")
        return

    # Sınırsız döngü: Parçalanacak child kalmadığında otomatik durur
    # We use a simple iterative approach to propagate amounts down
    all_child_requirements = []
    current_level_df = df_current.copy()

    while True:
        parents = list(current_level_df['item_id'].unique())
        if not parents:
             break

        # Reçete bileşenlerini çek
        query_bom = """
        SELECT parent_id, child_id, amount as bom_multiplier 
        FROM bom 
        WHERE parent_id = ANY(%s)
        """
        df_bom = run_query(query_bom, (parents,))
        
        if df_bom.empty:
            break
            
        # Join: Parent Miktarı * BOM Adedi
        df_merged = current_level_df.merge(df_bom, left_on='item_id', right_on='parent_id', how='inner')
        df_merged['child_amount'] = df_merged['amount'] * df_merged['bom_multiplier']
        
        # Aggregation: Aynı child_id and date için topla
        df_next_level = df_merged.groupby(['child_id', 'date'])['child_amount'].sum().reset_index()
        df_next_level.rename(columns={'child_amount': 'amount'}, inplace=True)
        
        # Store for final batch upsert
        all_child_requirements.append(df_next_level)
        
        # Prepare for next level
        current_level_df = df_next_level.rename(columns={'child_id': 'item_id'})

    if not all_child_requirements:
        logger.info("Alt bileşenlere ihtiyaç bulunmadı.")
        return

    # Combine all levels and aggregate by item/date (a component might appear in multiple levels)
    df_combined = pd.concat(all_child_requirements)
    df_final = df_combined.groupby(['child_id', 'date'])['amount'].sum().reset_index()

    # Fetch item metadata for components
    child_ids = list(df_final['child_id'].unique())
    query_items = "SELECT item_id, item_type, item_quantity_type FROM item WHERE item_id = ANY(%s)"
    df_items = run_query(query_items, (child_ids,))
    
    df_upsert = df_final.merge(df_items, left_on='child_id', right_on='item_id', how='left')

    # Batch Upsert into safety_stock_plan
    insert_query = """
    INSERT INTO safety_stock_plan (item_id, date, ai_amount, is_approved, item_type, item_quantity_type)
    VALUES (%s, %s, %s, FALSE, %s, %s)
    ON CONFLICT (item_id, date) DO UPDATE SET 
        ai_amount = EXCLUDED.ai_amount, 
        is_approved = FALSE;
    """
    
    rows_to_insert = [
        (
            row['child_id'], 
            row['date'], 
            round(row['amount'], 5), 
            row['item_type'],
            row['item_quantity_type']
        ) 
        for _, row in df_upsert.iterrows()
    ]
    
    run_command_batch(insert_query, rows_to_insert)
    logger.info(f"TUM BOM PARCALAMA TAMAMLANDI. {len(rows_to_insert)} bileşen güncellendi.")

if __name__ == "__main__":
    run_bom_explosion()
