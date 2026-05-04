import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import pandas as pd
from datetime import date, datetime
import psycopg2 

# Add backend root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.logger import get_logger
logger = get_logger(__name__)

from backend import config
try:
    from backend.crud import safety_stock, forecast
    from backend.AI_ML import prophet_algo as prophet, lightgbm_algo as lightgbm
except ImportError as e:
    logger.warning(f"Warning: Could not import local modules: {e}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



class ForecastUpdate(BaseModel):
    item_id: str
    date: str
    amount: float = Field(..., ge=0)

class ApprovalItem(BaseModel):
    item_id: str
    date: str
    amount: float = Field(..., ge=0)
    preference: Optional[str] = 'AI'
    item_quantity_type: Optional[str] = None

# --- Helper for Graceful Error Handling ---
def handle_db_error(e):
    err_msg = str(e)
    if isinstance(e, psycopg2.errors.ForeignKeyViolation):
        raise HTTPException(status_code=409, detail=f"İşlem yapılamadı: Kayıt başka bir yerde kullanılıyor. (FK Error)")
    if isinstance(e, psycopg2.errors.UniqueViolation):
        raise HTTPException(status_code=409, detail=f"Bu kayıt zaten mevcut.")
    if "update or delete on table" in err_msg and "violates foreign key constraint" in err_msg:
         raise HTTPException(status_code=409, detail="Bu kayıt silinemez çünkü başka verilerle ilişkili (Sipariş veya Reçete).")
    
    # Generic Internal Error
    logger.error(f"DB Error: {e}")
    raise HTTPException(status_code=500, detail=err_msg)


@app.get("/")
def read_root():
    return {"message": "AI-Driven MRP System API is Running (Refactored)"}



# ---------------------------------------------------------
# 7. Demand Forecast
# ---------------------------------------------------------

@app.get("/api/forecast/temporary")
def get_forecast():
    try:
        df = forecast.get_forecast_data()
        if not df.empty and 'date' in df.columns:
            df['date'] = df['date'].astype(str)
            
        return df.fillna("").to_dict(orient="records")
    except Exception as e:
        handle_db_error(e)

@app.put("/api/forecast/update")
def update_forecast_row(body: ForecastUpdate):
    try:
        forecast.update_forecast_data(body.item_id, body.date, body.amount)
        return {"status": "success"}
    except Exception as e:
        handle_db_error(e)

@app.post("/api/forecast/calculate")
def calculate_forecast():
    try:
        prophet.run_full_analysis()

        return {"status": "success", "message": "Calculation completed."}
    except Exception as e:
        handle_db_error(e)

@app.post("/api/forecast/approve-row")
def post_approve_forecast_row(data: dict):
    try:
        forecast.approve_forecast_row(data['item_id'], data['date'])
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/forecast/approve")
def post_approve_forecast():
    try:
        forecast.approve_forecast()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/forecast/detail/{item_id}")
def get_forecast_detail_endpoint(item_id: str):
    try:
        data = forecast.get_forecast_detail(item_id)
        return data
    except Exception as e:
        handle_db_error(e)


# ---------------------------------------------------------
# 9. Safety Stock AI (refactored)
# ---------------------------------------------------------
@app.get("/api/safety-stock")
def get_safety_stock():
    try:
        current_month_start = date.today().replace(day=1).strftime("%Y-%m-%d")
        df_final = safety_stock.get_final_safety_stock(current_month_start)
        
        if not df_final.empty:
             if 'date' in df_final.columns:
                df_final['date'] = df_final['date'].astype(str)
             return df_final.to_dict(orient="records")
            
        return []
    except Exception as e:
        handle_db_error(e)

@app.get("/api/safety-stock/temporary")
def get_safety_stock_temporary():
    try:
        df_ai = safety_stock.get_calculated_safety_stock_temp()
        if not df_ai.empty and 'date' in df_ai.columns:
            df_ai['date'] = df_ai['date'].astype(str)
            
        df_formula = safety_stock.get_kings_formula_results()
        df_active = safety_stock.get_all_active_safety_stock()
        
        if not df_ai.empty:
            df_merged = df_ai.merge(df_formula, on='item_id', how='left')
            df_merged['formula_result'] = df_merged['formula_result'].fillna(0).round(5)
            
            # Merge active safety stock for preference persistence
            if not df_active.empty:
                df_merged = df_merged.merge(df_active, left_on=['item_id', 'date'], right_on=['item_id', 'active_date'], how='left')
            else:
                df_merged['active_safety_stock'] = None
                
            import numpy as np
            df_merged = df_merged.replace({np.nan: None})
            return df_merged.to_dict(orient="records")
            
        return []
    except Exception as e:
        handle_db_error(e)

@app.post("/api/safety-stock/calculate")
def calculate_safety_stock_endpoint():
    try:
        safety_stock.calculate_safety_stock()
        return {"status": "success"}
    except Exception as e:
        handle_db_error(e)

@app.post("/api/safety-stock/approve")
def approve_safety_stock(approval_list: List[ApprovalItem]):
    try:
        count = safety_stock.approve_safety_stock_plan(approval_list)
        return {"status": "success", "count": count}
    except Exception as e:
        handle_db_error(e)



@app.get("/api/consumption/{item_id}")
def get_consumption_endpoint(item_id: str):
    try:
        from backend.database.db_helper import run_query
        # 1. Historical Consumption & Approved Safety Stock
        sql_history = """
        SELECT 
            COALESCE(c.date, s.date)::text as date,
            c.amount as consumption,
            s.safety_amount as historical_ss
        FROM consume c
        FULL OUTER JOIN safety_stock_history s ON c.item_id = s.item_id AND c.date = s.date
        WHERE COALESCE(c.item_id, s.item_id) = %s
        ORDER BY date ASC
        """
        
        # 2. Future Suggested AI (Current Plan)
        sql_future = """
        SELECT date::text as date, ai_amount as future_ai
        FROM safety_stock_plan
        WHERE item_id = %s AND date >= DATE_TRUNC('month', CURRENT_DATE)::DATE
        ORDER BY date ASC
        """
        
        df_hist = run_query(sql_history, (item_id,))
        df_future = run_query(sql_future, (item_id,))
        
        # Combine them in a way the chart can consume
        # We can just return a dict with both or merge them. Merging is usually easier for the chart.
        if df_hist.empty and df_future.empty:
            return []
            
        import pandas as pd
        df_merged = pd.concat([df_hist, df_future]).groupby('date').first().reset_index()
        df_merged = df_merged.sort_values('date')
        
        return df_merged.fillna(0).to_dict(orient="records")
    except Exception as e:
        handle_db_error(e)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.BACKEND_PORT)
