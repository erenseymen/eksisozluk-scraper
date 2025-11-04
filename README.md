# Ekşi Sözlük Scraper

Terminal tabanlı Ekşi Sözlük scraper'ı. Çıktısı AI-friendly formatlarda: JSON (varsayılan), CSV ve Markdown.

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

Scraper, çıktı formatını dosya uzantısından otomatik olarak tespit eder:

```bash
# JSON formatı (varsayılan)
python eksisozluk_scraper.py "başlık-adı" --output sonuclar.json

# CSV formatı
python eksisozluk_scraper.py "başlık-adı" --output sonuclar.csv

# Markdown formatı
python eksisozluk_scraper.py "başlık-adı" --output sonuclar.md
# veya
python eksisozluk_scraper.py "başlık-adı" --output sonuclar.markdown
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

## Özellikler

- ✅ Terminal tabanlı CLI arayüzü
- ✅ Tab completion desteği (bash/zsh)
- ✅ Çoklu çıktı formatı desteği (JSON, CSV, Markdown)
- ✅ Format otomatik tespiti (dosya uzantısından)
- ✅ AI-friendly JSON çıktı formatı (varsayılan)
- ✅ Başlık bazlı tüm entry scraping
- ✅ Zaman aralığına göre filtreleme (gün/hafta/ay/yıl)
- ✅ Spesifik entry'den itibaren scraping
- ✅ Rate limiting (sane pauses)
- ✅ Hata durumunda otomatik retry mekanizması
- ✅ Debian paket desteği
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

## Tab Completion

The scraper supports tab completion for bash and zsh shells. After installation:

### Bash
```bash
# If using Debian package, completion is automatically installed
# Otherwise, activate manually:
source <(register-python-argcomplete eksisozluk-scraper)

# Or add to ~/.bashrc:
eval "$(register-python-argcomplete eksisozluk-scraper)"
```

### Zsh
```bash
# Activate argcomplete for zsh
autoload -U bashcompinit
bashcompinit
eval "$(register-python-argcomplete eksisozluk-scraper)"
```

### Usage
After activation, you can use tab completion:
```bash
eksisozluk-scraper <TAB>              # Shows input prompt
eksisozluk-scraper --<TAB>             # Shows all options
eksisozluk-scraper --output <TAB>      # Completes file names (.json, .csv, .md)
```

## Debian Package Installation

### Building the Package

See [BUILD.md](BUILD.md) for detailed build instructions.

Quick build:
```bash
# Install build dependencies
sudo apt-get install build-essential debhelper dh-python python3-all python3-setuptools

# Build package
make build-deb

# Install package
sudo dpkg -i ../eksisozluk-scraper_*.deb
sudo apt-get install -f  # Install missing dependencies if any
```

### Using the Installed Package

After installation, the `eksisozluk-scraper` command is available system-wide:
```bash
eksisozluk-scraper "python" --days 7 --output results.json
```

Tab completion is automatically enabled if bash-completion is installed.

## Notlar

- Scraper, Ekşi Sözlük'e aşırı yük bindirmemek için her request arasında varsayılan 1.5 saniye bekler.
- Hata durumlarında otomatik olarak belirli aralıklarla tekrar dener.
- Tab completion requires `argcomplete` package to be installed.

