# OptiStock AI - Talep Tahmini ve Güvenlik Stoğu Modülü

OptiStock AI, şirketlerin mevcut Kurumsal Kaynak Planlama (ERP) veya MRP sistemlerine entegre edilmek üzere veri bilimi odaklı tasarlanmış, bağımsız bir **Yapay Zeka (AI/ML) Modülüdür**.

> [!WARNING]  
> **ÖNEMLİ NOT (Entegrasyon Köprüsü):**  
> Bu proje tek başına çalışan tam teşekküllü bir ERP sistemi (stok girişi, fatura kesimi, üretim kaydı vb.) **değildir.** Bu sistem sadece yapay zeka analizlerini yapan ve sonuçları sunan izole bir modüldür. Şirketin ana veritabanındaki geçmiş satış, tüketim ve ürün verilerinin bu sistemin veritabanına aktarılması için geliştirici ekip tarafından bir **veri köprüsü (data pipeline / entegrasyon yazılımı)** yazılması gerekmektedir.

## 🚀 Temel Özellikler

Bu modül iki temel yapay zeka analizine odaklanmaktadır:

### 1. Talep Tahmini (Demand Forecast) - Prophet Algoritması
- Şirketin geçmiş tüketim ve satış verilerini (zaman serisi verilerini) analiz ederek gelecekteki ürün taleplerini öngörür.
- **Facebook Prophet** algoritması kullanılarak ürünlerin mevsimselliği (seasonality), trendleri ve geçmiş satış tatilleri/anormallikleri hesaba katılır.
- Tahmin sonuçları veritabanına işlenir ve ön yüzde *infinite scroll* (sonsuz kaydırma) destekli grafiklerle kullanıcıya detaylı olarak görselleştirilir.

### 2. Güvenlik Stoğu (Safety Stock) - LightGBM Algoritması
- **LightGBM** makine öğrenmesi modeli kullanılarak; ürünlerin tedarik süreleri (lead time) ve geçmişteki talep sapmaları analiz edilir.
- Sistem sadece yapay zeka modeliyle değil, aynı zamanda geleneksel istatistiksel yöntemlerle (King's Formula) de güvenlik stoğu seviyelerini hesaplar.
- Kullanıcıya, AI'ın önerisi ile matematiksel formülün sonucunu karşılaştırıp en uygun olanı (veya manuel bir değeri) onaylayıp sisteme kaydetme imkanı sunar.

---

## 🔗 Veri Entegrasyon İhtiyacı (Köprü Kurulumu)

Bu modülün çalışabilmesi ve yapay zeka analizlerinin (Prophet & LightGBM) doğru sonuç üretebilmesi için, ana ERP sistemindeki ham verilerin bu modüle ait veritabanındaki **temel tablolara** (entegrasyon köprüsü ile) aktarılması şarttır.

**Köprü Yazılımı ile Doldurulması Gereken Tablolar:**
1. **`item`**: Tüm ürün, hammadde ve yarı mamül kartları.
2. **`supplier_item`**: Ürünlerin tedarikçileri ve ortalama tedarik süreleri (lead time).
3. **`purchase`**: Geçmiş satınalma siparişleri ve gecikme süreleri (Hammadde tedarik sapma analizi için).
4. **`sales_out_history` & `warehouse_movements`**: Geçmiş satışlar ve depo içi tüketim/sarfiyat hareketleri (Zaman serisi talep tahmini için).
5. **`bom` (Ürün Ağacı):** Ürünlerin içerik reçeteleri. *(Not: Eğer şirketinizin ana sisteminde ürün ağaçları "Level" (hiyerarşik seviyeli) yapıda tutuluyorsa, proje içindeki `translate.py` modülü bu level'lı BOM yapısını otomatik olarak bizim sistemimizin okuyabileceği formata dönüştürebilir).*

> [!TIP]
> **Doldurulmaması Gereken Tablolar (Sistem Kendi Üretir):**
> Prophet ve LightGBM algoritmalarının ürettiği tahminleri, AI sonuçlarını ve sistem geçmişini kaydeden aşağıdaki tablolara dışarıdan veri **yazılmamalıdır**. Bu tabloları AI modülü kendisi yönetir:
> - `prophet_table_temporary`, `prophet_table_history`
> - `safety_stock_plan`, `safety_stock_history`, `ss_kings_formula`

> [!NOTE]
> **Özelleştirme İhtiyacı (Depo / Üretim Hattı Kodu):**
> Yapay zeka modellerimiz (LightGBM), hammaddelerin *gerçekten üretime girip girmediğini* (tüketimi) anlamak için `warehouse_movements` (depo hareketleri) tablosunu analiz eder. Sistemin varsayılan kodlarında, hedef deposu (target_warehouse) **`HK`** harfleriyle başlayan hareketler "Üretime Çıkış / Tüketim" olarak kabul edilmektedir.
> Eğer entegre edeceğiniz şirketin üretim depo kodları farklıysa (örneğin "URETIM", "HAT-1" vb.); bu filtreleme mantığını **`backend/AI_ML/lightgbm_algo.py`** ve **`backend/AI_ML/lightgbm_backtest.py`** dosyalarındaki `target_warehouse LIKE 'HK%'` yazan SQL sorgularını bularak kendi şirketinizin kodlarına göre kesinlikle değiştirmelisiniz.

---

## 💻 Kullanılan Teknolojiler

- **Arkayüz (Backend):** Python, FastAPI, Pandas, SQLAlchemy (Psycopg2)
- **Makine Öğrenmesi (AI/ML):** LightGBM, Prophet
- **Önyüz (Frontend):** React, Vite, TailwindCSS, Recharts
- **Veritabanı:** PostgreSQL

---

## ⚙️ Konfigürasyon ve Kurulum

Sistemin çalışabilmesi için bilgisayarınızda **Python**, **Node.js (npm)** ve **PostgreSQL** yüklü olmalıdır.

### 1. Veritabanı ve Port Ayarları (.env)
Proje kök dizininde bulunan `.env` dosyasında (ve sistemin içindeki konfigürasyonlarda) varsayılan olarak `name`, `sifre`, `port no` gibi yer tutucu (placeholder) metinler bulunmaktadır. Sistemi ayağa kaldırmadan önce bu değişkenleri **kendi ortamınıza göre kesinlikle güncellemelisiniz**:

```env
# Database Configuration
DB_NAME= name          # Veritabanı adı (örneğin: sirket_db)
DB_USER= postgres      # PostgreSQL kullanıcı adı
DB_PASSWORD= sifre     # PostgreSQL şifreniz
DB_HOST= localhost     # Veritabanı adresi
DB_PORT= port no       # Veritabanı portu (genelde 5432'dir)

# Service Ports
BACKEND_PORT= port no  # Backend API'nin çalışacağı port (ör: 8000)
FRONTEND_PORT= port no # Frontend arayüzünün çalışacağı port (ör: 5173)
```

### 2. Bağımlılıkların Kurulması

**Backend (Arkayüz) İçin:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend (Önyüz) İçin:**
```bash
cd frontend
npm install
```

---

## 🏃‍♂️ Projeyi Başlatma

Aşağıdaki komutları farklı terminal pencerelerinde çalıştırarak servisleri başlatabilirsiniz:

**Terminal 1 (Arkayüz - Backend):**
- Arkayüz klasörüne gidin: `cd backend`
- Servisi başlatın: `python main.py`
*(Swagger API Dokümantasyonu: http://localhost:8000/docs)*

**Terminal 2 (Önyüz - Frontend):**
- Önyüz klasörüne gidin: `cd frontend`
- Arayüzü başlatın: `npm run dev`
*(Web Arayüzü: http://localhost:5173)*
