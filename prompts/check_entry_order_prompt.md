## Entry Sıralaması Test Promptu

Aşağıdaki adımları aynı sırayla uygula ve scraper çıktısının tarih sıralamasını doğrula:

1. `python eksisozluk_scraper.py galatasaray --max-entries 29`
2. `python eksisozluk_scraper.py galatasaray --max-entries 29 --years 1`
3. `python eksisozluk_scraper.py https://eksisozluk.com/entry/52103 --max-entries 29`

Her komut için:
- Dönen JSON çıktısındaki `entries` listesinde `date` alanlarının kronolojik olarak artan sırada (en eski → en yeni) olduğunu kontrol et. Saat/dakika bilgisi olan kayıtlar da zinciri bozmayacak şekilde artmalı.
- Güncelleme içeren tarih formatları (`~`) varsa, temel tarih değerinin sıralamayı bozmadığından emin ol.

Ek doğrulama:
- `https://eksisozluk.com/galatasaray--33210` sayfasını açarak ilk sayfanın scraper çıktısıyla tutarlı şekilde eski → yeni sıralandığını manuel kontrol et.

Notlar:
- Gerekirse farklı başlıklar veya `--years` değerleriyle aynı kontrolü tekrarlayarak regresyon yakala.
- Çıktıda sıralama hatası görürsen ilgili komutun tam çıktısını kaydet ve hata raporuna ekle.

