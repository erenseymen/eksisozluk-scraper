# Fish completion for eksisozluk-scraper
# This file is part of eksisozluk-scraper package

# Positional argument: input (başlık adı veya entry URL'si)
# Note: We allow free text here since it can be either a title or URL
complete -c eksisozluk-scraper -n "test (count (commandline -poc)) -eq 1" -a "(__fish_complete_path)"

# Options
complete -c eksisozluk-scraper -l days -d "Son N günlük entry'leri scrape et" -r
complete -c eksisozluk-scraper -l weeks -d "Son N haftalık entry'leri scrape et" -r
complete -c eksisozluk-scraper -l months -d "Son N aylık entry'leri scrape et" -r
complete -c eksisozluk-scraper -l years -d "Son N yıllık entry'leri scrape et" -r
complete -c eksisozluk-scraper -l delay -d "Request'ler arası bekleme süresi (saniye, varsayılan: 1.5)" -r
complete -c eksisozluk-scraper -l max-retries -d "Maksimum tekrar deneme sayısı (varsayılan: 3)" -r
complete -c eksisozluk-scraper -l retry-delay -d "Retry arası bekleme süresi (saniye, varsayılan: 5.0)" -r
complete -c eksisozluk-scraper -l max-entries -d "Maksimum entry sayısı (varsayılan: sınırsız)" -r
complete -c eksisozluk-scraper -l output -s o -d "Çıktı dosyası (.json, .csv, .md, .markdown)" -r -f -a "(__fish_complete_suffix .json .csv .md .markdown)"
complete -c eksisozluk-scraper -l no-bkz -d "Referans edilen entry'leri fetch etme (bkz özelliğini devre dışı bırak)"
complete -c eksisozluk-scraper -l help -s h -d "Yardım mesajını göster"

