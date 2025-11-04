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

## Kurulum

[![Debian Package](https://img.shields.io/badge/Debian-Download-blue?style=for-the-badge&logo=debian)](https://github.com/erenseymen/eksisozluk-scraper/releases/download/v1.1.0/eksisozluk-scraper_1.1.0-1_all.deb)
[![RPM Package](https://img.shields.io/badge/RPM-Download-red?style=for-the-badge&logo=redhat)](https://github.com/erenseymen/eksisozluk-scraper/releases/download/v1.1.0/eksisozluk-scraper-1.1.0-1.noarch.rpm)
[![AUR Package](https://img.shields.io/badge/AUR-Install-yellow?style=for-the-badge&logo=arch-linux)](https://aur.archlinux.org/packages/eksisozluk-scraper)
[![Windows Executable](https://img.shields.io/badge/Windows-Download-blue?style=for-the-badge&logo=windows)](https://github.com/erenseymen/eksisozluk-scraper/releases/download/v1.1.0/eksisozluk-scraper.exe)

### Alternatif metod: Python Script Olarak Çalıştırma

Python scriptini doğrudan çalıştırabilirsiniz:

```bash
# Bağımlılıkları kur
pip3 install -r requirements.txt

# Scripti çalıştır
python3 eksisozluk_scraper.py "başlık adı"
```

## Kullanım

### Temel Kullanım

```bash
# Başlıktaki tüm entry'leri scrape et
eksisozluk-scraper "başlık adı"

### Zaman Filtreleme

```bash
# Son 1 günlük entry'ler
eksisozluk-scraper "başlık adı" --days 1

# Son 2 haftalık entry'ler
eksisozluk-scraper "başlık adı" --weeks 2

# Son 1 aylık entry'ler
eksisozluk-scraper "başlık adı" --months 1

# Son 1 yıllık entry'ler
eksisozluk-scraper "başlık adı" --years 1
```

### Maksimum Entry Sayısı

```bash
# Maksimum 100 entry scrape et
eksisozluk-scraper "başlık adı" --max-entries 100
```

### Belirli Entry'den İtibaren Scrape Etme

```bash
eksisozluk-scraper "https://eksisozluk.com/entry/entry-id"
```

### Çıktıyı Dosyaya Kaydetme

Scraper, çıktı formatını dosya uzantısından otomatik olarak tespit eder:

```bash
# JSON formatı (varsayılan)
eksisozluk-scraper "başlık adı" --output sonuclar.json

# CSV formatı
eksisozluk-scraper "başlık adı" --output sonuclar.csv

# Markdown formatı
eksisozluk-scraper "başlık adı" --output sonuclar.md
# veya
eksisozluk-scraper "başlık adı" --output sonuclar.markdown
```

### Gelişmiş Parametreler

```bash
# Request'ler arası bekleme süresi (varsayılan: 1.5 saniye)
eksisozluk-scraper "başlık adı" --delay 2.0

# Maksimum retry sayısı (varsayılan: 3)
eksisozluk-scraper "başlık adı" --max-retries 5

# Retry arası bekleme (varsayılan: 5.0 saniye)
eksisozluk-scraper "başlık adı" --retry-delay 10.0

# Referans edilen entry'leri fetch etme (varsayılan: True)
eksisozluk-scraper "başlık adı" --no-bkz
```

## Notlar

- Scraper, Ekşi Sözlük'e aşırı yük bindirmemek için her request arasında varsayılan 1.5 saniye bekler.
- Hata durumlarında otomatik olarak belirli aralıklarla tekrar dener.
