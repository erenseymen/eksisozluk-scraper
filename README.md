# Ekşi Sözlük Scraper

Terminal tabanlı Ekşi Sözlük scraper'ı. Çıktısı AI-friendly JSON formatında.

## Kurulum

```bash
# Virtual environment oluştur (önerilir)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows

# Bağımlılıkları kur
pip install -r requirements.txt
```

## Kullanım

### Başlıktaki Tüm Entry'leri Scrape Etme

```bash
python eksisozluk_scraper.py "başlık-adı"
```

### Zaman Filtreleme

```bash
# Son 1 günlük entry'ler
python eksisozluk_scraper.py "başlık-adı" --days 1

# Son 1 haftalık entry'ler
python eksisozluk_scraper.py "başlık-adı" --days 7

# Son 2 haftalık entry'ler
python eksisozluk_scraper.py "başlık-adı" --weeks 2
```

### Belirli Entry'den İtibaren Scrape Etme

```bash
python eksisozluk_scraper.py "https://eksisozluk.com/başlık-adı--entry-id"
```

### Çıktıyı Dosyaya Kaydetme

```bash
python eksisozluk_scraper.py "başlık-adı" --output sonuclar.json
```

### Gelişmiş Parametreler

```bash
# Request'ler arası bekleme süresi (varsayılan: 1.5 saniye)
python eksisozluk_scraper.py "başlık-adı" --delay 2.0

# Maksimum retry sayısı (varsayılan: 3)
python eksisozluk_scraper.py "başlık-adı" --max-retries 5

# Retry arası bekleme (varsayılan: 5.0 saniye)
python eksisozluk_scraper.py "başlık-adı" --retry-delay 10.0
```

## Çıktı Formatı

Scraper, AI tarafından kolayca işlenebilecek JSON formatında çıktı üretir:

```json
{
  "scrape_info": {
    "timestamp": "2024-01-12T15:30:00",
    "total_entries": 42,
    "input": "python",
    "time_filter": "1 days"
  },
  "entries": [
    {
      "entry_id": "123456",
      "entry_url": "https://eksisozluk.com/python--123456",
      "title": "python",
      "date": "12.01.2024 15:30",
      "author": "kullanıcı_adı",
      "content": "Entry içeriği...",
      "favorite_count": 5,
      "entry_number": "1"
    }
  ]
}
```

## Özellikler

- ✅ Terminal tabanlı CLI arayüzü
- ✅ AI-friendly JSON çıktı formatı
- ✅ Başlık bazlı tüm entry scraping
- ✅ Zaman aralığına göre filtreleme (gün/hafta)
- ✅ Spesifik entry'den itibaren scraping
- ✅ Rate limiting (sane pauses)
- ✅ Hata durumunda otomatik retry mekanizması
- ✅ Otomatik test suite

## Testler

Proje, otomatik test suite'i içerir. Testleri çalıştırmak için:

```bash
# Tüm testleri çalıştır
python test_scraper.py

# veya
./test_scraper.py
```

Test suite aşağıdaki özellikleri doğrular:
- ✅ Temel scraping işlevselliği
- ✅ Pagination'ın doğru sayfada durması
- ✅ Zaman filtresi kullanırken ters sıralama
- ✅ Doğru pagination URL formatı (`/slug--id?p=X`)
- ✅ Son sayfa numarasının doğru tespit edilmesi (`data-pagecount`)
- ✅ Entry yapı doğrulaması
- ✅ Rate limiting

## Notlar

- Scraper, Ekşi Sözlük'e aşırı yük bindirmemek için her request arasında varsayılan 1.5 saniye bekler.
- Hata durumlarında otomatik olarak belirli aralıklarla tekrar dener.

