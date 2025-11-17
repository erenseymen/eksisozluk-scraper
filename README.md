# eksisozluk-scraper

Terminal tabanlı Ekşi Sözlük scraper'ı. JSON, CSV ve Markdown çıktıları üretir; Gemini CLI ile özet/blog oluşturabilir.

## Özellikler

- Tarih, entry sayısı ve özel filtreler uygulayabilme
- Referans verilen link ve YouTube transkript içeriğini toplama
- Rate limit, retry mekanizması
- Gemini CLI entegrasyonu (özet/blog/prompt)

## Kurulum

- **Pipx (önerilen)**: `pipx install eksisozluk-scraper` veya `pipx install git+https://github.com/erenseymen/eksisozluk-scraper.git`
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
eksisozluk-scraper "başlık" --filter "python|asyncio" --filter concurrency
eksisozluk-scraper "başlık" --filter-urls
eksisozluk-scraper "https://eksisozluk.com/entry/123456"

# Çıktı biçimleri
eksisozluk-scraper "başlık" --output sonuclar.json
eksisozluk-scraper "başlık" --output sonuclar.csv
eksisozluk-scraper "başlık" --output sonuclar.md

# Gelişmiş ayarlar
eksisozluk-scraper "başlık" --delay 2 --max-retries 5 --retry-delay 10 --no-bkz
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
