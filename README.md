# eksisozluk-scraper

Terminal tabanlı Ekşi Sözlük scraper'ı. Çıktısı AI-friendly formatlarda: JSON (varsayılan), CSV ve Markdown.

## Özellikler

- ✅ Terminal tabanlı CLI arayüzü
- ✅ Tab completion desteği (bash/zsh/fish)
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

## Kurulum

### Yöntem 1: Debian/Ubuntu Paketi (Önerilen)

Debian/Ubuntu sistemlerde hazır paketi kullanarak kurulum yapabilirsiniz:

```bash
# Paketi indirin ve kurun
sudo dpkg -i eksisozluk-scraper_1.0.0-1_all.deb

# Eksik bağımlılıkları yükleyin (gerekirse)
sudo apt-get install -f
```

Kurulumdan sonra `eksisozluk-scraper` komutu sistem genelinde kullanılabilir olacaktır.

**Not:** Paket, bash ve fish completion desteğini otomatik olarak yükler. Yeni bir terminal açtığınızda tab completion aktif olacaktır.

### Yöntem 2: Python Script Olarak Çalıştırma

Python scriptini doğrudan çalıştırabilirsiniz:

```bash
# Bağımlılıkları kur
pip3 install -r requirements.txt

# Scripti çalıştır
python3 eksisozluk_scraper.py "başlık-adı"
```

### Yöntem 3: Python Paketi Olarak Kurulum (Geliştirme)

Geliştirme için paketi editable modda kurabilirsiniz:

```bash
# Virtual environment oluştur (önerilir)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows

# Paketi kur
pip install -e .

# Artık eksisozluk-scraper komutunu kullanabilirsiniz
eksisozluk-scraper "başlık-adı"
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

# Son 1 haftalık entry'ler
eksisozluk-scraper "başlık-adı" --days 7

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

## Tab Completion

Scraper, bash, zsh ve fish shell'leri için tab completion desteği sunar.

### Debian Paketi ile Kurulum

Debian paketi ile kurulum yaptıysanız, bash ve fish completion otomatik olarak yüklenir. Yeni bir terminal açtığınızda tab completion aktif olacaktır.

### Manuel Aktifleştirme

Eğer tab completion çalışmıyorsa:

#### Bash

```bash
# Manuel aktifleştirme
source <(register-python-argcomplete eksisozluk-scraper)

# veya ~/.bashrc'ye ekleyin:
eval "$(register-python-argcomplete eksisozluk-scraper)"
```

#### Zsh

```bash
# Zsh için argcomplete'i aktifleştir
autoload -U bashcompinit
bashcompinit
eval "$(register-python-argcomplete eksisozluk-scraper)"

# veya ~/.zshrc'ye ekleyin:
autoload -U bashcompinit
bashcompinit
eval "$(register-python-argcomplete eksisozluk-scraper)"
```

#### Fish

Fish completion için iki seçenek vardır:

**Yöntem 1: Debian Paketi ile (Önerilen)**
Debian paketi ile kurulum yaptıysanız, Fish completion otomatik olarak `/usr/share/fish/vendor_completions.d/` dizinine yüklenir ve aktif olur.

**Yöntem 2: Manuel Kurulum**
Eğer manuel kurulum yaptıysanız, completion dosyasını kopyalayın:

```fish
# Completion dosyasını kopyala
cp completions/eksisozluk-scraper.fish ~/.config/fish/completions/

# Yeni bir terminal açın veya completion'ı yeniden yükleyin
```

### Kullanım

Tab completion aktif olduktan sonra:

```bash
eksisozluk-scraper <TAB>              # Seçenekleri gösterir
eksisozluk-scraper --<TAB>             # Tüm flag'leri listeler
eksisozluk-scraper --output <TAB>      # Dosya isimlerini tamamlar (.json, .csv, .md)
```

**Not:** Bash ve zsh için tab completion için `argcomplete` paketinin kurulu olması gerekir (Debian paketi ile otomatik yüklenir). Fish completion için `argcomplete` gerekmez, Fish'in kendi completion sistemi kullanılır.

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

## Paket Oluşturma

Debian paketi oluşturmak için detaylı bilgi [BUILD.md](BUILD.md) dosyasına bakın.

Hızlı paket oluşturma:

```bash
# Build bağımlılıklarını kur
sudo apt-get install build-essential debhelper dh-python python3-all python3-setuptools

# Paketi oluştur
make build-deb
```

## Sorun Giderme

### Tab Completion Çalışmıyor

**Bash/Zsh için:**
1. `argcomplete` paketinin kurulu olduğundan emin olun:
   ```bash
   pip3 install argcomplete
   ```

2. Completion'ı manuel aktifleştirin (yukarıdaki Tab Completion bölümüne bakın)

3. Yeni bir terminal açın

**Fish için:**
1. Completion dosyasının doğru konumda olduğundan emin olun:
   - Sistem geneli: `/usr/share/fish/vendor_completions.d/eksisozluk-scraper.fish`
   - Kullanıcı: `~/.config/fish/completions/eksisozluk-scraper.fish`

2. Yeni bir terminal açın veya completion'ı yeniden yükleyin:
   ```fish
   source ~/.config/fish/completions/eksisozluk-scraper.fish
   ```

### Paket Kurulum Hataları

Eğer paket kurulumu bağımlılık hataları verirse:

```bash
sudo apt-get install -f
sudo apt-get install python3-pip
```

### İzin Hataları

Eğer izin hataları alıyorsanız, çalıştırılabilir dosyanın PATH'te olduğundan emin olun:

```bash
which eksisozluk-scraper
```

Bulunamazsa, paketi yeniden kurun veya tam yolu kullanın.

## Notlar

- Scraper, Ekşi Sözlük'e aşırı yük bindirmemek için her request arasında varsayılan 1.5 saniye bekler.
- Hata durumlarında otomatik olarak belirli aralıklarla tekrar dener.
- Tab completion için `argcomplete` paketi gereklidir (Debian paketi ile otomatik yüklenir).

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## Katkıda Bulunma

Katkılarınızı bekliyoruz! Lütfen pull request göndermeden önce testleri çalıştırdığınızdan emin olun.

## İletişim

Sorularınız veya önerileriniz için issue açabilirsiniz.
