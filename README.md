# eksisozluk-scraper

Terminal tabanlı Ekşi Sözlük scraper'ı. JSON, CSV ve Markdown çıktıları üretir; Gemini CLI ile özet/blog oluşturabilir.

## Özellikler

- Tarih, entry sayısı ve özel filtreler uygulayabilme
- Referans verilen link ve YouTube transkript içeriğini toplama
- Rate limit, retry mekanizması
- Gemini CLI entegrasyonu (özet/blog/prompt)

## Kurulum

- Debian: [eksisozluk-scraper_2.0.1-1_all.deb](https://github.com/erenseymen/eksisozluk-scraper/releases/download/v2.0.1/eksisozluk-scraper_2.0.1-1_all.deb)
- RPM: [eksisozluk-scraper-2.0.1-1.noarch.rpm](https://github.com/erenseymen/eksisozluk-scraper/releases/download/v2.0.1/eksisozluk-scraper-2.0.1-1.noarch.rpm)
- AUR: [`eksisozluk-scraper`](https://aur.archlinux.org/packages/eksisozluk-scraper)
- Pip: `pip install eksisozluk-scraper` veya `pip install git+https://github.com/erenseymen/eksisozluk-scraper.git`
- Kaynaktan: `git clone ... && pip install -r requirements.txt && python eksisozluk_scraper.py "başlık"`

## Komut Örnekleri

```bash
# Temel kullanım
eksisozluk-scraper "başlık"

# Tarih/süre filtreleri
eksisozluk-scraper "başlık" --start 2024.01.01 --end 2024.02.01
eksisozluk-scraper "başlık" --days 1

# Entry ve içerik filtreleri
eksisozluk-scraper "başlık" --filter python --filter asyncio
eksisozluk-scraper "başlık" --filter-urls
eksisozluk-scraper "https://eksisozluk.com/entry/123456"

# Çıktı biçimleri
eksisozluk-scraper "başlık" --output sonuclar.json
eksisozluk-scraper "başlık" --output sonuclar.csv
eksisozluk-scraper "başlık" --output sonuclar.md

# Gelişmiş ayarlar
eksisozluk-scraper "başlık" --delay 2 --max-retries 5 --retry-delay 10 --no-bkz
```

## Çıktı Yapısı

Her entry, `entry_number`, `has_external_url` ve `referenced_content` (entry/url/youtube detayları) alanlarıyla gelir. Harici linkler için trafilatura özetleri, YouTube için transkript ve kimlik bilgileri eklenir.

```json
{
  "title": "the beatles",
  "entry_id": "123456",
  "content": "...",
  "referenced_content": [
    {"type": "entry", "title": "john lennon", "entry_id": "654321"},
    {"type": "youtube", "url": "https://youtu.be/abc123xyz78"}
  ]
}
```

## Gemini CLI

- Kurulum: [geminicli.com](https://geminicli.com/)
- Özet: `eksisozluk-scraper "başlık" --ozet`
- Blog: `eksisozluk-scraper "başlık" --blog --months 1`
- Özel prompt: `eksisozluk-scraper "başlık" --prompt "Analiz et" -o cikti.json`
- Flash modeli: `--ozet --flash`

## Notlar

- Rate limit ve retry mekanizması varsayılan olarak aktiftir.
- Gemini özellikleri için Gemini CLI kurulu ve giriş yapılmış olmalıdır.
