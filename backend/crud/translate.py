import pandas as pd
import sys
import os
from sqlalchemy import create_engine

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.db_helper import run_query, run_command, run_command_batch
from backend.logger import get_logger
from backend.config import EXT_DB_CONFIG

logger = get_logger(__name__)

def get_external_engine():
    """Dış PostgreSQL veritabanına bağlantı engine'i oluşturur."""
    conn_str = f"postgresql://{EXT_DB_CONFIG['user']}:{EXT_DB_CONFIG['password']}@{EXT_DB_CONFIG['host']}:{EXT_DB_CONFIG['port']}/{EXT_DB_CONFIG['dbname']}"
    return create_engine(conn_str)

def sync_bom_from_external_db(external_table_name="external_bom_table"):
    """
    Dış veritabanındaki hiyerarşik BOM verisini çeker ve 
    bizim yerel (parent_id, child_id) yapımıza dönüştürerek kaydeder.
    """
    logger.info(f"Dış veritabanından veri çekiliyor: {external_table_name}")
    
    try:
        engine = get_external_engine()
        query = f"SELECT * FROM {external_table_name}"
        df = pd.read_sql(query, engine)
    except Exception as e:
        logger.error(f"Dış veritabanına bağlanırken/okurken hata oluştu: {e}")
        return False

    if df.empty:
        logger.warning("Dış tablodan veri dönmedi.")
        return False

    # 1. Gerekli kolonları kontrol et
    required_cols = ['exploded_level', 'parent_exploded_id', 'exploded_id', 
                     'b_item_id_patlatılmış', 'miktar', 'birim', 'satir_tipi',
                     'b_item_id_mamul']
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"Dış tabloda eksik kolon: {col}")
            return False

    # 2. Ürünleri (Item) Senkronize Et
    logger.info("Ürünler senkronize ediliyor...")
    all_items = df[['b_item_id_patlatılmış', 'birim', 'satir_tipi']].drop_duplicates()
    
    # Birim mapping (Gerekirse burada düzenleme yapılabilir)
    unit_map = {
        'Adet': 'adet', 'ADET': 'adet', 'Ad': 'adet',
        'Kg': 'kg', 'KG': 'kg',
        'Metre': 'm', 'M': 'm',
        'Lt': 'lt', 'Litre': 'lt'
    }

    item_insert_query = """
    INSERT INTO item (item_id, item_type, item_quantity_type)
    VALUES (%s, %s, %s)
    ON CONFLICT (item_id) DO UPDATE SET 
        item_type = EXCLUDED.item_type,
        item_quantity_type = EXCLUDED.item_quantity_type;
    """
    
    item_batch = []
    for _, row in all_items.iterrows():
        item_id = str(row['b_item_id_patlatılmış'])
        raw_type = str(row['satir_tipi']).lower()
        
        # Tip eşleştirme
        item_type = 'hammadde'
        if 'mamul' in raw_type or 'mamül' in raw_type:
            item_type = 'mamul'
        elif 'yarı' in raw_type or 'yari' in raw_type:
            item_type = 'yari_mamul'
            
        unit = unit_map.get(row['birim'], 'adet')
        item_batch.append((item_id, item_type, unit))
    
    run_command_batch(item_insert_query, item_batch)

    # 3. BOM İlişkilerini Dönüştür
    logger.info("BOM hiyerarşisi dönüştürülüyor...")
    bom_relations = []
    
    # Her ana mamul bazında grupla (Çünkü exploded_id'ler mamul bazında lokaldir)
    for mamul_id, group in df.groupby('b_item_id_mamul'):
        # exploded_id -> item_id haritası oluştur
        id_map = {row['exploded_id']: str(row['b_item_id_patlatılmış']) for _, row in group.iterrows()}
        
        for _, row in group.iterrows():
            parent_exp_id = row['parent_exploded_id']
            
            # Eğer parent_exploded_id listede varsa ve kendisi değilse (Root değilse)
            if parent_exp_id in id_map and row['exploded_id'] != parent_exp_id:
                parent_real_id = id_map[parent_exp_id]
                child_real_id = str(row['b_item_id_patlatılmış'])
                miktar = float(row['miktar'])
                
                bom_relations.append((parent_real_id, child_real_id, miktar))

    # 4. Veritabanına Yaz
    if not bom_relations:
        logger.warning("Kaydedilecek BOM ilişkisi bulunamadı.")
        return False

    # Mükerrer ilişkileri temizle (Farklı mamullerin altında aynı alt montajlar olabilir)
    bom_df = pd.DataFrame(bom_relations, columns=['parent_id', 'child_id', 'amount'])
    bom_df = bom_df.drop_duplicates(subset=['parent_id', 'child_id'])
    
    logger.info(f"Mevcut BOM tablosu temizleniyor ve {len(bom_df)} yeni ilişki ekleniyor...")
    run_command("TRUNCATE bom")
    
    bom_insert_query = "INSERT INTO bom (parent_id, child_id, amount) VALUES (%s, %s, %s)"
    final_batch = [tuple(x) for x in bom_df.values]
    
    if run_command_batch(bom_insert_query, final_batch):
        logger.info("✅ BOM Senkronizasyonu Başarıyla Tamamlandı!")
        return True
    else:
        logger.error("❌ BOM Kayıt Hatası!")
        return False

if __name__ == "__main__":
    # Test için çalıştırılabilir
    sync_bom_from_external_db()
