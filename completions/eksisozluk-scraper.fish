# Fish completion for eksisozluk-scraper
# This file is part of eksisozluk-scraper package

# Positional argument: input (başlık adı veya entry URL'si)
# Note: We allow free text here since it can be either a title or URL
complete -c eksisozluk-scraper -n "test (count (commandline -poc)) -eq 1" -a "(__fish_complete_path)"

# Options
complete -c eksisozluk-scraper -s h -l help -d "Yardım mesajını göster"
complete -c eksisozluk-scraper -s v -l version -d "Program versiyonunu göster ve çık"

complete -c eksisozluk-scraper -s d -l days -d "Son N günlük entry'leri scrape et" -r
complete -c eksisozluk-scraper -s w -l weeks -d "Son N haftalık entry'leri scrape et" -r
complete -c eksisozluk-scraper -s m -l months -d "Son N aylık entry'leri scrape et" -r
complete -c eksisozluk-scraper -s y -l years -d "Son N yıllık entry'leri scrape et" -r
complete -c eksisozluk-scraper -s s -l start -d "Belirli bir başlangıç tarihinden itibaren entry'leri dahil et (YYYY.MM.DD)" -r
complete -c eksisozluk-scraper -s e -l end -d "Belirli bir bitiş tarihine kadar entry'leri dahil et (YYYY.MM.DD)" -r

complete -c eksisozluk-scraper -s D -l delay -d "Request'ler arası bekleme süresi (saniye, varsayılan: 0.0)" -r
complete -c eksisozluk-scraper -s R -l max-retries -d "Maksimum tekrar deneme sayısı (varsayılan: 3)" -r
complete -c eksisozluk-scraper -s T -l retry-delay -d "Retry arası bekleme süresi (saniye, varsayılan: 1.0)" -r
complete -c eksisozluk-scraper -s n -l max-entries -d "Maksimum entry sayısı (varsayılan: sınırsız)" -r

complete -c eksisozluk-scraper -s o -l output -d "Çıktı dosyası (uzantıya göre format tespit edilir)" -r -f -a "(__fish_complete_suffix .json .csv .md .markdown)"
complete -c eksisozluk-scraper -s B -l no-bkz -d "Referans edilen entry'leri dahil etme (bkz özelliğini kapat)"
complete -c eksisozluk-scraper -l fetch -d "Harici URL içeriklerini ve YouTube transkriptlerini getir"
complete -c eksisozluk-scraper -s f -l filter -d "Entry içeriklerinde anahtar kelimeleri filtrele (birden fazla olabilir)" -r
complete -c eksisozluk-scraper -s u -l filter-urls -d "Yalnızca Ekşi Sözlük dışı URL içeren entry'leri getir"
complete -c eksisozluk-scraper -s r -l reverse -d "Entry'leri ters sırada tara (son sayfadan başla)"

# Gemini CLI entegrasyonu
complete -c eksisozluk-scraper -s z -l ozet -d "Gemini CLI ile özet oluştur ve stdout'a yazdır"
complete -c eksisozluk-scraper -s b -l blog -d "Gemini CLI ile blog yazısı oluştur ve stdout'a yazdır"
complete -c eksisozluk-scraper -s p -l prompt -d "Gemini CLI ile özel prompt kullanarak çıktı oluştur" -r
complete -c eksisozluk-scraper -s F -l flash -d "Gemini CLI'de flash modelini kullan"

