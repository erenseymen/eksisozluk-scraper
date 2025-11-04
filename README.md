# eksisozluk-scraper

Terminal tabanlı Ekşi Sözlük scraper'ı. Çıktısı AI-friendly formatlarda: JSON (varsayılan), CSV ve Markdown.

Cursor (yapay zeka) ile yazılmıştır.

## Özellikler

- ✅ Terminal tabanlı CLI arayüzü
- ✅ Tab completion desteği (bash/zsh/fish)
- ✅ Çoklu çıktı formatı desteği (JSON, CSV, Markdown)
- ✅ Format otomatik tespiti (dosya uzantısından)
- ✅ Başlık bazlı tüm entry scraping
- ✅ Zaman aralığına göre filtreleme (gün/hafta/ay/yıl)
- ✅ Spesifik entry'den itibaren scraping
- ✅ Rate limiting
- ✅ Hata durumunda otomatik retry mekanizması
- ✅ Debian paket desteği
- ✅ Arch Linux (AUR) paket desteği

## Kurulum

### Yöntem 1: Debian/Ubuntu Paketi (Önerilen)

Debian/Ubuntu sistemlerde hazır paketi kullanarak kurulum yapabilirsiniz:

```bash
# Paketi indirin ve kurun
sudo dpkg -i eksisozluk-scraper_1.1.0-1_all.deb

# Eksik bağımlılıkları yükleyin (gerekirse)
sudo apt-get install -f
```

Kurulumdan sonra `eksisozluk-scraper` komutu sistem genelinde kullanılabilir olacaktır.

**Not:** Paket, bash ve fish completion desteğini otomatik olarak yükler. Yeni bir terminal açtığınızda tab completion aktif olacaktır.

### Yöntem 2: Arch Linux (AUR)

Arch Linux kullanıcıları için AUR paketi mevcuttur:

```bash
# AUR helper ile (örnek: yay)
yay -S eksisozluk-scraper

# veya manuel olarak
git clone https://aur.archlinux.org/eksisozluk-scraper.git
cd eksisozluk-scraper
makepkg -si
```

Kurulumdan sonra `eksisozluk-scraper` komutu sistem genelinde kullanılabilir olacaktır.

**Not:** Paket, bash ve fish completion desteğini otomatik olarak yükler. Yeni bir terminal açtığınızda tab completion aktif olacaktır.

### Yöntem 3: Python Script Olarak Çalıştırma

Python scriptini doğrudan çalıştırabilirsiniz:

```bash
# Bağımlılıkları kur
pip3 install -r requirements.txt

# Scripti çalıştır
python3 eksisozluk_scraper.py "başlık-adı"
```

## Kullanım

### Temel Kullanım

```bash
# Başlıktaki tüm entry'leri scrape et
eksisozluk-scraper "başlık-adı"

# veya Python script ile
python3 eksisozluk_scraper.py "başlık-adı"
```

### Zaman Filtreleme

```bash
# Son 1 günlük entry'ler
eksisozluk-scraper "başlık-adı" --days 1

# Son 2 haftalık entry'ler
eksisozluk-scraper "başlık-adı" --weeks 2

# Son 1 aylık entry'ler
eksisozluk-scraper "başlık-adı" --months 1

# Son 1 yıllık entry'ler
eksisozluk-scraper "başlık-adı" --years 1
```

### Maksimum Entry Sayısı

```bash
# Maksimum 100 entry scrape et
eksisozluk-scraper "başlık-adı" --max-entries 100
```

### Belirli Entry'den İtibaren Scrape Etme

```bash
eksisozluk-scraper "https://eksisozluk.com/başlık-adı--entry-id"
```

### Çıktıyı Dosyaya Kaydetme

Scraper, çıktı formatını dosya uzantısından otomatik olarak tespit eder:

```bash
# JSON formatı (varsayılan)
eksisozluk-scraper "başlık-adı" --output sonuclar.json

# CSV formatı
eksisozluk-scraper "başlık-adı" --output sonuclar.csv

# Markdown formatı
eksisozluk-scraper "başlık-adı" --output sonuclar.md
# veya
eksisozluk-scraper "başlık-adı" --output sonuclar.markdown
```

### Gelişmiş Parametreler

```bash
# Request'ler arası bekleme süresi (varsayılan: 1.5 saniye)
eksisozluk-scraper "başlık-adı" --delay 2.0

# Maksimum retry sayısı (varsayılan: 3)
eksisozluk-scraper "başlık-adı" --max-retries 5

# Retry arası bekleme (varsayılan: 5.0 saniye)
eksisozluk-scraper "başlık-adı" --retry-delay 10.0

# Referans edilen entry'leri fetch etme (varsayılan: True)
eksisozluk-scraper "başlık-adı" --no-bkz
```

## Çıktı Formatları

Scraper, üç farklı çıktı formatını destekler. Format, dosya uzantısından otomatik olarak tespit edilir:

- **JSON** (varsayılan): `.json` uzantılı dosyalar veya uzantı belirtilmemişse
- **CSV**: `.csv` uzantılı dosyalar
- **Markdown**: `.md` veya `.markdown` uzantılı dosyalar

### JSON Formatı

JSON formatı (varsayılan), AI tarafından kolayca işlenebilecek yapıdadır:

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

### CSV Formatı

CSV formatı, veri analizi ve Excel gibi programlarda kullanım için uygundur. Sadece temel alanları içerir: `entry_id`, `title`, `date`, `author`, `content`.

### Markdown Formatı

Markdown formatı, okunabilir ve yapılandırılmış bir çıktı üretir. Her entry için başlık, tarih, yazar ve içerik bilgileri ayrı ayrı gösterilir.

## Notlar

- Scraper, Ekşi Sözlük'e aşırı yük bindirmemek için her request arasında varsayılan 1.5 saniye bekler.
- Hata durumlarında otomatik olarak belirli aralıklarla tekrar dener.
