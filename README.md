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

### Linux Paketleri

[![Debian Package](https://img.shields.io/badge/Debian-Download-blue?style=for-the-badge&logo=debian)](https://github.com/erenseymen/eksisozluk-scraper/releases/download/v1.1.0/eksisozluk-scraper_1.1.0-1_all.deb)
[![RPM Package](https://img.shields.io/badge/RPM-Download-red?style=for-the-badge&logo=redhat)](https://github.com/erenseymen/eksisozluk-scraper/releases/download/v1.1.0/eksisozluk-scraper-1.1.0-1.noarch.rpm)
[![AUR Package](https://img.shields.io/badge/AUR-Install-yellow?style=for-the-badge&logo=arch-linux)](https://aur.archlinux.org/packages/eksisozluk-scraper)

### Windows

[![Windows Executable](https://img.shields.io/badge/Windows-Download-blue?style=for-the-badge&logo=windows)](https://github.com/erenseymen/eksisozluk-scraper/releases)

#### Windows Executable (Önerilen)

Windows için hazırlanmış `.exe` dosyasını indirip doğrudan kullanabilirsiniz:

1. [Releases sayfasından](https://github.com/erenseymen/eksisozluk-scraper/releases) `eksisozluk-scraper.exe` dosyasını indirin
2. İndirilen dosyayı istediğiniz bir klasöre koyun (örneğin: `C:\tools\`)
3. Windows PowerShell veya Command Prompt'ta kullanın:

```cmd
REM Tam yol ile çalıştırma
C:\tools\eksisozluk-scraper.exe "başlık adı"
```

**PATH'e Ekleme (İsteğe Bağlı):**

Komutu her yerden çalıştırmak için executable'ı PATH'e ekleyebilirsiniz:

1. Windows Ayarlar > Sistem > Hakkında > Gelişmiş sistem ayarları
2. Ortam Değişkenleri > Kullanıcı değişkenleri > Path > Düzenle
3. Yeni ekle ve executable'ın bulunduğu klasörü ekleyin (örneğin: `C:\tools`)
4. PowerShell veya CMD'yi yeniden başlatın

Artık sadece komut adıyla çalıştırabilirsiniz:
```cmd
eksisozluk-scraper.exe "başlık adı"
```

**Not:** İlk çalıştırmada Windows Defender veya antivirüs yazılımı uyarı verebilir. Bu durumda "Daha fazla bilgi" > "Yine de çalıştır" seçeneğini kullanabilirsiniz. Bu, PyInstaller ile paketlenmiş executable'lar için normal bir durumdur.

#### Windows'ta Python Script Olarak Çalıştırma

Eğer Python yüklüyse, scripti doğrudan çalıştırabilirsiniz:

```powershell
# PowerShell'de
# Bağımlılıkları kur
pip install -r requirements.txt

# Scripti çalıştır
python eksisozluk_scraper.py "başlık adı"
```

#### Windows'ta Executable Oluşturma (Geliştiriciler için)

Kaynak kodundan Windows executable oluşturmak için:

**PowerShell ile:**
```powershell
.\build-windows.ps1
```

**Command Prompt ile:**
```cmd
build-windows.bat
```

Build işlemi tamamlandıktan sonra executable `dist\eksisozluk-scraper.exe` konumunda olacaktır.

### Alternatif metod: Python Script Olarak Çalıştırma (Linux/Mac)

Python scriptini doğrudan çalıştırabilirsiniz:

```bash
# Bağımlılıkları kur
pip3 install -r requirements.txt

# Scripti çalıştır
python3 eksisozluk_scraper.py "başlık adı"
```

## Kullanım

### Temel Kullanım

**Linux/Mac:**
```bash
# Başlıktaki tüm entry'leri scrape et
eksisozluk-scraper "başlık adı"
```

**Windows:**
```cmd
REM Command Prompt veya PowerShell'de
eksisozluk-scraper.exe "başlık adı"
```

veya Python scripti olarak:
```powershell
python eksisozluk_scraper.py "başlık adı"
```

### Zaman Filtreleme

**Linux/Mac:**
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

**Windows:**
```cmd
REM Command Prompt veya PowerShell'de
eksisozluk-scraper.exe "başlık adı" --days 1
eksisozluk-scraper.exe "başlık adı" --weeks 2
eksisozluk-scraper.exe "başlık adı" --months 1
eksisozluk-scraper.exe "başlık adı" --years 1
```

### Maksimum Entry Sayısı

**Linux/Mac:**
```bash
# Maksimum 100 entry scrape et
eksisozluk-scraper "başlık adı" --max-entries 100
```

**Windows:**
```cmd
eksisozluk-scraper.exe "başlık adı" --max-entries 100
```

### Belirli Entry'den İtibaren Scrape Etme

**Linux/Mac:**
```bash
eksisozluk-scraper "https://eksisozluk.com/entry/entry-id"
```

**Windows:**
```cmd
eksisozluk-scraper.exe "https://eksisozluk.com/entry/entry-id"
```

### Çıktıyı Dosyaya Kaydetme

Scraper, çıktı formatını dosya uzantısından otomatik olarak tespit eder:

**Linux/Mac:**
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

**Windows:**
```cmd
REM JSON formatı (varsayılan)
eksisozluk-scraper.exe "başlık adı" --output sonuclar.json

REM CSV formatı
eksisozluk-scraper.exe "başlık adı" --output sonuclar.csv

REM Markdown formatı
eksisozluk-scraper.exe "başlık adı" --output sonuclar.md
```

### Gelişmiş Parametreler

**Linux/Mac:**
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

**Windows:**
```cmd
REM Request'ler arası bekleme süresi (varsayılan: 1.5 saniye)
eksisozluk-scraper.exe "başlık adı" --delay 2.0

REM Maksimum retry sayısı (varsayılan: 3)
eksisozluk-scraper.exe "başlık adı" --max-retries 5

REM Retry arası bekleme (varsayılan: 5.0 saniye)
eksisozluk-scraper.exe "başlık adı" --retry-delay 10.0

REM Referans edilen entry'leri fetch etme (varsayılan: True)
eksisozluk-scraper.exe "başlık adı" --no-bkz
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
