import psycopg2
from psycopg2 import sql
import sys
import os

# Add backend to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import DB_CONFIG
from backend.logger import get_logger

logger = get_logger(__name__)

def create_tables():
    """
    Tablo yapılarını oluşturur.
    """
    commands = [
        # 0. Enum Types
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'item_type_enum') THEN
                CREATE TYPE item_type_enum AS ENUM ('mamül', 'yarı_mamül', 'hammadde');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'quantity_type_enum') THEN
                CREATE TYPE quantity_type_enum AS ENUM ('gram', 'adet', 'litre', 'kg', 'paket');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'movement_purpose_enum') THEN
                CREATE TYPE movement_purpose_enum AS ENUM ('üretime_giden', 'satış_çıkışı', 'giriş', 'çıkış');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'purchase_purpose_enum') THEN
                CREATE TYPE purchase_purpose_enum AS ENUM ('emniyet_stoku_için', 'acil_sipariş', 'normal_sipariş');
            END IF;

        END$$;
        """,

        # 1. item (Diğer tabloların bağımlı olduğu ana tablo)
        """
        CREATE TABLE IF NOT EXISTS item (
            item_id VARCHAR(20) PRIMARY KEY,
            item_type item_type_enum,
            item_quantity_type quantity_type_enum,
            demand_avg DECIMAL(18, 5),
            demand_deviation DECIMAL(18, 5)
        )
        """,
        
        # 2. supplier_item (item tablosuna bağımlı)
        """
        CREATE TABLE IF NOT EXISTS supplier_item (
            item_id VARCHAR(20) REFERENCES item(item_id),
            supplier_id VARCHAR(20),
            leadtime_avg DECIMAL(18, 5) DEFAULT 0,
            leadtime_deviation DECIMAL(18, 5) DEFAULT 0,
            PRIMARY KEY (item_id, supplier_id)
        )
        """,
        
        # 3. sales_out_history
        """
        CREATE TABLE IF NOT EXISTS sales_out_history (
            id SERIAL PRIMARY KEY,
            item_id VARCHAR(20) REFERENCES item(item_id),
            amount DECIMAL(18, 5),
            date DATE
        )
        """,
        
        # 4. warehouse_movements (New: For LightGBM Production Consumption)
        """
        CREATE TABLE IF NOT EXISTS warehouse_movements (
            id SERIAL PRIMARY KEY,
            item_id VARCHAR(20) REFERENCES item(item_id),
            date DATE,
            source_warehouse VARCHAR(50),
            target_warehouse VARCHAR(50),
            amount DECIMAL(18, 5)
        )
        """,
        
        # 6. Prophet Tables (1:1 Reference Alignment)
        """
        CREATE TABLE IF NOT EXISTS prophet_table_temporary (
            item_id VARCHAR(20) REFERENCES item(item_id),
            date DATE,
            amount DECIMAL(18, 5),
            yhat_lower DECIMAL(18, 5),
            yhat_upper DECIMAL(18, 5),
            is_approved BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (item_id, date)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS prophet_table_history (
            item_id VARCHAR(20) REFERENCES item(item_id),
            date DATE,
            amount DECIMAL(18, 5),
            yhat_lower DECIMAL(18, 5),
            yhat_upper DECIMAL(18, 5),
            is_approved BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (item_id, date)
        )
        """,
        
        # 7. safety_stock_plan (Unified Table)
        """
        CREATE TABLE IF NOT EXISTS safety_stock_plan (
            item_id VARCHAR(20) REFERENCES item(item_id),
            date DATE,
            ai_amount DECIMAL(18, 5) DEFAULT 0,
            formula_amount DECIMAL(18, 5) DEFAULT 0,
            manual_amount DECIMAL(18, 5),
            is_approved BOOLEAN DEFAULT FALSE,
            item_type item_type_enum,
            item_quantity_type quantity_type_enum,
            PRIMARY KEY (item_id, date)
        )
        """,
        # 8. safety_stock_history (Historical Approved Values)
        """
        CREATE TABLE IF NOT EXISTS safety_stock_history (
            id SERIAL PRIMARY KEY,
            item_id VARCHAR(20) REFERENCES item(item_id),
            date DATE,
            safety_amount DECIMAL(18, 5),
            UNIQUE (item_id, date)
        )
        """,

        # 9.6. bom (Bill of Materials)
        """
        CREATE TABLE IF NOT EXISTS bom (
            parent_id VARCHAR(20) REFERENCES item(item_id),
            child_id VARCHAR(20) REFERENCES item(item_id),
            amount DECIMAL(18, 5),
            PRIMARY KEY (parent_id, child_id)
        )
        """,
        
        # 10. purchase
        """
        CREATE TABLE IF NOT EXISTS purchase (
            id SERIAL PRIMARY KEY,
            item_id VARCHAR(20) REFERENCES item(item_id),
            supplier_id VARCHAR(20),
            amount DECIMAL(18, 5),
            purchase_date DATE,
            expected_coming_date DATE,
            actual_coming_date DATE,
            delay_day NUMERIC GENERATED ALWAYS AS (actual_coming_date - expected_coming_date) STORED,
            purpose purchase_purpose_enum,
            FOREIGN KEY (item_id, supplier_id) REFERENCES supplier_item(item_id, supplier_id)
        )
        """,



        
        # 12. ss_kings_formula (item ve supplier_item tablolarına bağımlı)
        """
        CREATE TABLE IF NOT EXISTS ss_kings_formula (
            item_id VARCHAR(20) REFERENCES item(item_id),
            supplier_id VARCHAR(20),
            demand_avg DECIMAL(18, 5),
            leadtime_avg DECIMAL(18, 5),
            demand_deviation DECIMAL(18, 5),
            leadtime_deviation DECIMAL(18, 5),
            z_score NUMERIC DEFAULT 1.64,
            result_king NUMERIC GENERATED ALWAYS AS (
                z_score * SQRT(
                    (leadtime_avg * demand_deviation * demand_deviation) + 
                    (demand_avg * demand_avg * leadtime_deviation * leadtime_deviation)
                )
            ) STORED,
            PRIMARY KEY (item_id, supplier_id),
            FOREIGN KEY (item_id, supplier_id) REFERENCES supplier_item(item_id, supplier_id)
        )
        """,

        # 14. Cross-Table Sync Triggers (ss_kings_formula <-> supplier_item)
        """
        CREATE OR REPLACE FUNCTION propagate_supplier_item_changes() RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                INSERT INTO ss_kings_formula (item_id, supplier_id)
                VALUES (NEW.item_id, NEW.supplier_id)
                ON CONFLICT (item_id, supplier_id) DO NOTHING;
            ELSIF TG_OP = 'UPDATE' THEN
                UPDATE ss_kings_formula
                SET
                    leadtime_avg = NEW.leadtime_avg,
                    leadtime_deviation = NEW.leadtime_deviation
                WHERE item_id = NEW.item_id AND supplier_id = NEW.supplier_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        
        """
        DROP TRIGGER IF EXISTS trigger_propagate_supplier_changes ON supplier_item;
        CREATE TRIGGER trigger_propagate_supplier_changes
        AFTER INSERT OR UPDATE ON supplier_item
        FOR EACH ROW
        EXECUTE FUNCTION propagate_supplier_item_changes();
        """,
        
        """
        CREATE OR REPLACE FUNCTION fetch_ss_parameters() RETURNS TRIGGER AS $$
        DECLARE
            src_row supplier_item%ROWTYPE;
            item_row item%ROWTYPE;
        BEGIN
            -- 1. Fetch Leadtime from supplier_item
            SELECT * INTO src_row FROM supplier_item 
            WHERE item_id = NEW.item_id AND supplier_id = NEW.supplier_id;
            
            IF FOUND THEN
                NEW.leadtime_avg := src_row.leadtime_avg;
                NEW.leadtime_deviation := src_row.leadtime_deviation;
            END IF;

            -- 2. Fetch Demand from item
            SELECT * INTO item_row FROM item WHERE item_id = NEW.item_id;
            IF FOUND THEN
                NEW.demand_avg := item_row.demand_avg;
                NEW.demand_deviation := item_row.demand_deviation;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        
        """
        DROP TRIGGER IF EXISTS trigger_fetch_ss_parameters ON ss_kings_formula;
        CREATE TRIGGER trigger_fetch_ss_parameters
        BEFORE INSERT OR UPDATE ON ss_kings_formula
        FOR EACH ROW
        EXECUTE FUNCTION fetch_ss_parameters();
        """,
        
        # 14.5 Sync Logic (Push Demand from Item to SS)
        """
        CREATE OR REPLACE FUNCTION propagate_item_demand_changes() RETURNS TRIGGER AS $$
        BEGIN
            UPDATE ss_kings_formula
            SET 
                demand_avg = NEW.demand_avg,
                demand_deviation = NEW.demand_deviation
            WHERE item_id = NEW.item_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        
        """
        DROP TRIGGER IF EXISTS trigger_propagate_item_demand ON item;
        CREATE TRIGGER trigger_propagate_item_demand
        AFTER UPDATE OF demand_avg, demand_deviation ON item
        FOR EACH ROW
        EXECUTE FUNCTION propagate_item_demand_changes();
        """,
        

        
        # 16. Dynamic Demand Calc (Item Type Based) + Helper Function
        """
        CREATE OR REPLACE FUNCTION update_item_demand_stats() RETURNS TRIGGER AS $$
        DECLARE
            target_item_id VARCHAR(20);
            item_t item_type_enum;
            avg_val DECIMAL(18, 5);
            std_val DECIMAL(18, 5);
        BEGIN
            -- On UPDATE with item_id change: recalculate BOTH old and new items
            IF TG_OP = 'UPDATE' AND OLD.item_id != NEW.item_id THEN
                -- 1. Recalculate OLD item's demand (reverse old effect)
                PERFORM _recalc_demand(OLD.item_id);
                -- 2. Recalculate NEW item's demand (apply new effect)
                PERFORM _recalc_demand(NEW.item_id);
                RETURN NEW;
            END IF;

            -- Standard: pick the right item_id
            IF TG_OP = 'DELETE' THEN
                target_item_id := OLD.item_id;
            ELSE
                target_item_id := NEW.item_id;
            END IF;
            
            PERFORM _recalc_demand(target_item_id);
            
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        
        """
        CREATE OR REPLACE FUNCTION _recalc_demand(p_item_id VARCHAR(20)) RETURNS VOID AS $$
        DECLARE
            item_t item_type_enum;
            avg_val DECIMAL(18, 5);
            std_val DECIMAL(18, 5);
        BEGIN
            SELECT item_type INTO item_t FROM item WHERE item_id = p_item_id;
            
            IF item_t = 'hammadde' THEN
                -- 1. Hammadde: Tüm münferit satınalma (purchase) kayıtlarının ortalamasına bak (Sipariş bazlı)
                SELECT AVG(amount), STDDEV(amount) 
                INTO avg_val, std_val
                FROM purchase 
                WHERE item_id = p_item_id;
                
            ELSIF item_t = 'mamül' THEN
                -- 2. Mamül: Tüm münferit dış satış (sales_out_history) kayıtlarının ortalamasına bak (İşlem bazlı)
                SELECT AVG(amount), STDDEV(amount) 
                INTO avg_val, std_val
                FROM sales_out_history 
                WHERE item_id = p_item_id;
            
            ELSIF item_t = 'yarı_mamül' THEN
                -- 3. Yarı Mamül: Hibrit Mantık (Münferit İşlemler)
                -- (Doğrudan münferit satışlar + Üst ürünlerin satışlarından gelen reçeteli ihtiyaçlar)
                WITH RECURSIVE bom_tree AS (
                    -- Başlangıç: Tüm satış kayıtları (Mamüller ve diğer satılan kalemler)
                    -- Not: Buradaki her bir 's.id' bir işlemi temsil eder.
                    SELECT s.id as tx_id, s.item_id as current_item, s.amount, 1.0::DECIMAL(18, 5) as multiplier
                    FROM sales_out_history s
                    
                    UNION ALL
                    
                    -- Parçalama: Üst işlem miktarlarını alt bileşenlere hiyerarşik olarak dağıt
                    SELECT bt.tx_id, b.child_id, bt.amount, bt.multiplier * b.amount
                    FROM bom_tree bt
                    JOIN bom b ON bt.current_item = b.parent_id
                ),
                total_tx_requirement AS (
                    -- Bu ürün için (p_item_id) tüm kaynak işlemlerden gelen paylar
                    SELECT tx_id, SUM(amount * multiplier) as tx_amount
                    FROM bom_tree
                    WHERE current_item = p_item_id
                    GROUP BY tx_id
                )
                SELECT AVG(tx_amount), STDDEV(tx_amount)
                INTO avg_val, std_val
                FROM total_tx_requirement;

            ELSE
                RETURN;
            END IF;
            
            UPDATE item 
            SET demand_avg = COALESCE(avg_val, 0), 
                demand_deviation = COALESCE(std_val, 0)
            WHERE item_id = p_item_id;
        END;
        $$ LANGUAGE plpgsql;
        """,
        
        """
        DROP TRIGGER IF EXISTS trigger_calc_demand_purchase ON purchase;
        CREATE TRIGGER trigger_calc_demand_purchase
        AFTER INSERT OR UPDATE OR DELETE ON purchase
        FOR EACH ROW
        EXECUTE FUNCTION update_item_demand_stats();
        """,
        
        """
        DROP TRIGGER IF EXISTS trigger_calc_demand_sales ON sales_out_history;
        CREATE TRIGGER trigger_calc_demand_sales
        AFTER INSERT OR UPDATE OR DELETE ON sales_out_history
        FOR EACH ROW
        EXECUTE FUNCTION update_item_demand_stats();
        """,
        


        



    ]

    try:
        # 1. Varsayilan 'postgres' veritabanina baglanarak hedef veritabanini olustur
        conn_default = psycopg2.connect(dbname='postgres', user=DB_CONFIG['user'], password=DB_CONFIG['password'], host=DB_CONFIG['host'], port=DB_CONFIG['port'])
        conn_default.autocommit = True
        cur_default = conn_default.cursor()
        
        cur_default.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_CONFIG['dbname']}'")
        exists = cur_default.fetchone()
        if not exists:
            logger.warning(f"Veritabani '{DB_CONFIG['dbname']}' bulunamadi, olusturuluyor...")
            cur_default.execute(f"CREATE DATABASE \"{DB_CONFIG['dbname']}\"")
            logger.info("Veritabani olusturuldu.")
        else:
             logger.info(f"Veritabani '{DB_CONFIG['dbname']}' zaten mevcut.")
             
        cur_default.close()
        conn_default.close()

        # 2. Simdi hedef veritabanina baglan
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Komutları sırayla çalıştır
        logger.info("Tablolar olusturuluyor...")
        for command in commands:
            # Tablo adını logla (basit bir parse işlemi ile)
            if "CREATE TABLE" in command:
                 try:
                    table_name = command.split("EXISTS")[1].split("(")[0].strip()
                    logger.info(f"- {table_name}")
                 except:
                    pass
            cur.execute(command)

        # Değişiklikleri kaydet
        conn.commit()


        logger.info("Tum tablolar basariyla olusturuldu!")

        cur.close()
        conn.close()

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Hata olustu: {error}")

if __name__ == '__main__':
    create_tables()
