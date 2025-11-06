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
- ✅ **Gemini CLI entegrasyonu** - AI destekli özet ve blog yazısı oluşturma

## Kurulum

[![Debian Package](https://img.shields.io/badge/Debian-Download-blue?style=for-the-badge&logo=debian)](https://github.com/erenseymen/eksisozluk-scraper/releases/download/v1.1.0/eksisozluk-scraper_1.1.0-1_all.deb)
[![RPM Package](https://img.shields.io/badge/RPM-Download-red?style=for-the-badge&logo=redhat)](https://github.com/erenseymen/eksisozluk-scraper/releases/download/v1.1.0/eksisozluk-scraper-1.1.0-1.noarch.rpm)
[![AUR Package](https://img.shields.io/badge/AUR-Install-yellow?style=for-the-badge&logo=arch-linux)](https://aur.archlinux.org/packages/eksisozluk-scraper)
[![Windows Executable](https://img.shields.io/badge/Windows-Download-blue?style=for-the-badge&logo=windows)](https://github.com/erenseymen/eksisozluk-scraper/releases/download/v1.1.0/eksisozluk-scraper.exe)

### Pip ile Kurulum (Pipx de deneyin)

```bash
pip install eksisozluk-scraper
```

ya da

```bash
pip install git+https://github.com/erenseymen/eksisozluk-scraper.git

```

### Alternatif metod: Python Script Olarak Çalıştırma

Python scriptini doğrudan çalıştırabilirsiniz:

```bash
# Repoyu klonla
git clone https://github.com/erenseymen/eksisozluk-scraper.git
cd eksisozluk-scraper

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
```

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
# Request'ler arası bekleme süresi (varsayılan: 0 saniye)
eksisozluk-scraper "başlık adı" --delay 2.0

# Maksimum retry sayısı (varsayılan: 3)
eksisozluk-scraper "başlık adı" --max-retries 5

# Retry arası bekleme (varsayılan: 1 saniye)
eksisozluk-scraper "başlık adı" --retry-delay 10.0

# Referans edilen entry'leri fetch etme (varsayılan: True)
eksisozluk-scraper "başlık adı" --no-bkz
```

### Çıktıyı Başka Komutlara Pipe Etme

```bash
# Çıktıyı Gemini'ye pipe ederek özetleme
eksisozluk-scraper "the beatles" --years 1 | gemini -p "entry'leri özetle"
```

## Gemini CLI entegrasyonu

Scraper, [Gemini CLI](https://github.com/google-gemini/gemini-cli) ile entegre çalışarak AI destekli özet ve blog yazıları oluşturabilir.

### Kurulum

Önce Gemini CLI'yi kurmanız gerekir:

https://geminicli.com/

### Kullanım

#### Özet Oluşturma

```bash
# Entry'leri özetle ve stdout'a yazdır
eksisozluk-scraper "the beatles" --ozet

# Özet oluştur ve dosyalara kaydet
eksisozluk-scraper "the beatles" --ozet -o beatles.json
# → beatles.json (JSON) ve beatles.md (Gemini özet) oluşturulur
```

#### Blog Yazısı Oluşturma

```bash
# Entry'lerden blog yazısı oluştur ve stdout'a yazdır
eksisozluk-scraper "the beatles" --blog

# Blog yazısı oluştur ve dosyalara kaydet
eksisozluk-scraper "the beatles" --blog -o beatles.json
# → beatles.json (JSON) ve beatles.md (Gemini blog) oluşturulur
```

#### Özel Prompt Kullanma

```bash
# Özel prompt ile çıktı oluştur
eksisozluk-scraper "the beatles" --prompt "Türk kullanıcıların The Beatles hakkındaki görüşlerini analiz et"

# Kısa form
eksisozluk-scraper "the beatles" -p "Entry'leri analiz et ve önemli noktaları listele"

# Özel prompt ile çıktı oluştur ve kaydet
eksisozluk-scraper "the beatles" -p "Analiz et" -o result.json
# → result.json (JSON) ve result.md (Gemini çıktı) oluşturulur

# Flash model ile özet oluştur
eksisozluk-scraper "the beatles" --ozet --flash

```

#### Zaman Filtresi ile Birlikte Kullanım

```bash
# Son 1 yıllık entry'leri özetle ve dosyaya kaydet
eksisozluk-scraper "the beatles" --years 1 --ozet -o beatles-2024.json
```

## Notlar

- Hata durumlarında otomatik olarak belirli aralıklarla tekrar dener.
- Gemini CLI entegrasyonu için Gemini CLI'nin kurulu olması ve Google hesabı ile giriş yapılmış olması gereklidir.
