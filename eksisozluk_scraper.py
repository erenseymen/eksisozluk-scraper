#!/usr/bin/env python3
"""
Ekşi Sözlük Scraper
Terminal tabanlı, AI-friendly output üreten scraper.
"""

import argparse
try:
    import argcomplete
except ImportError:
    argcomplete = None
import csv
import json
import re
import time
import sys
import signal
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs

import cloudscraper
from bs4 import BeautifulSoup


class EksisozlukScraper:
    """Ekşi Sözlük scraper sınıfı"""
    
    BASE_URL = "https://eksisozluk.com"
    
    def __init__(self, delay: float = 1.5, max_retries: int = 3, retry_delay: float = 5.0, output_file: Optional[str] = None, max_entries: Optional[int] = None, fetch_referenced: bool = True):
        """
        Args:
            delay: Her request arası bekleme süresi (saniye)
            max_retries: Maksimum tekrar deneme sayısı
            retry_delay: Hata aldığında tekrar denemeden önce bekleme süresi (saniye)
            output_file: Entry'lerin yazılacağı JSON dosyası yolu (opsiyonel)
            max_entries: Maksimum entry sayısı (opsiyonel, None ise sınırsız)
            fetch_referenced: Referans edilen entry'leri fetch et (varsayılan: True)
        """
        self.delay = delay
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.output_file = output_file
        self.max_entries = max_entries
        self.fetch_referenced = fetch_referenced
        self.scrape_start_time = None
        self.scrape_input = None
        self.scrape_time_filter = None
        self.current_entries = []  # Mevcut entry'leri tutmak için
        self.scraped_entry_ids = set()  # Scrape edilmiş entry ID'lerini tutmak için (duplikasyon önleme)
        # cloudscraper Cloudflare korumasını bypass eder
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'linux',
                'desktop': True
            }
        )
        # Ek header'lar
        self.session.headers.update({
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        })
    
    def _make_request(self, url: str):
        """HTTP request yapar, retry mekanizması ile"""
        attempt = 0
        
        while attempt < self.max_retries:
            try:
                response = self.session.get(url, timeout=10, allow_redirects=True)
                
                # 404 hatası sayfa yok demektir, retry yapma
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                return response
                
            except Exception as e:
                # HTTP hataları için kontrol et
                if hasattr(e, 'response') and e.response is not None:
                    if e.response.status_code == 404:
                        # 404 hatası sayfa yok demektir, retry yapma
                        return None
                
                attempt += 1
                if attempt < self.max_retries:
                    print(f"Uyarı: İstek hatası (deneme {attempt}/{self.max_retries}): {e}", file=sys.stderr)
                    time.sleep(self.retry_delay)
                else:
                    print(f"Hata: Maksimum deneme sayısına ulaşıldı: {url}", file=sys.stderr)
                    return None
        
        return None
    
    def _parse_entry(self, entry_element) -> Optional[Dict]:
        """Bir entry elementini parse eder - çoklu selector stratejisi ile"""
        try:
            entry_data = {}
            
            # Entry ID - data-id attribute'dan veya href'ten
            entry_id = None
            if entry_element.get('data-id'):
                entry_id = entry_element.get('data-id')
                entry_data['entry_id'] = entry_id
            else:
                # href'ten entry ID çıkar
                entry_id_elem = (entry_element.find('a', {'class': 'entry-date'}) or 
                               entry_element.find('a', class_=re.compile('entry.*date')) or
                               entry_element.find('a', href=re.compile(r'entry--\d+')))
                if entry_id_elem and entry_id_elem.get('href'):
                    href = entry_id_elem['href']
                    entry_id_match = re.search(r'entry--(\d+)', href)
                    if entry_id_match:
                        entry_id = entry_id_match.group(1)
                        entry_data['entry_id'] = entry_id
                        entry_data['entry_url'] = self.BASE_URL + href if href.startswith('/') else href
            
            if not entry_id:
                return None
            
            # Entry tarihi
            date_elem = (entry_element.find('a', {'class': 'entry-date'}) or
                        entry_element.find('a', class_=re.compile('entry.*date')) or
                        entry_element.find('span', class_=re.compile('date')) or
                        entry_element.find('time'))
            if date_elem:
                entry_data['date'] = date_elem.get_text(strip=True)
            
            # Yazar
            author_elem = (entry_element.find('a', {'class': 'entry-author'}) or
                          entry_element.find('a', class_=re.compile('entry.*author')) or
                          entry_element.find('a', class_=re.compile('author')) or
                          entry_element.find('span', {'class': 'entry-author'}) or
                          entry_element.find('span', class_=re.compile('author')))
            if author_elem:
                entry_data['author'] = author_elem.get_text(strip=True)
            
            # Entry içeriği - çoklu selector dene
            content_elem = (entry_element.find('div', {'class': 'content'}) or
                           entry_element.find('div', class_=re.compile('content')) or
                           entry_element.find('p') or
                           entry_element.find('div', {'class': 'entry-content'}))
            
            if content_elem:
                # Referans edilen entry ID'lerini bul (bkz linklerinden)
                referenced_entry_ids = []
                # Entry linklerini bul - href'te /entry/ veya entry-- olan linkler
                entry_links = content_elem.find_all('a', href=re.compile(r'(?:/entry/|entry--)\d+'))
                for link in entry_links:
                    href = link.get('href', '')
                    # /entry/123456 formatı
                    entry_match = re.search(r'/entry/(\d+)', href)
                    if entry_match:
                        ref_entry_id = entry_match.group(1)
                        if ref_entry_id != entry_id:  # Kendi kendine referans değilse
                            referenced_entry_ids.append(ref_entry_id)
                    else:
                        # entry--123456 formatı
                        entry_match = re.search(r'entry--(\d+)', href)
                        if entry_match:
                            ref_entry_id = entry_match.group(1)
                            if ref_entry_id != entry_id:  # Kendi kendine referans değilse
                                referenced_entry_ids.append(ref_entry_id)
                
                # Tekrarları kaldır
                referenced_entry_ids = list(set(referenced_entry_ids))
                if referenced_entry_ids:
                    entry_data['referenced_entry_ids'] = referenced_entry_ids  # İç kullanım için - sonra kaldırılacak
                
                # HTML tag'lerini temizle ama formatı koru
                for br in content_elem.find_all('br'):
                    br.replace_with('\n')
                for p in content_elem.find_all('p'):
                    p.append('\n')
                entry_data['content'] = content_elem.get_text(separator='\n', strip=True)
            
            # Fav sayısı
            fav_elem = (entry_element.find('span', {'class': 'fav-count'}) or
                       entry_element.find('span', class_=re.compile('fav')) or
                       entry_element.find('a', class_=re.compile('favorite')))
            if fav_elem:
                fav_text = fav_elem.get_text(strip=True)
                # Sayıları çıkar
                fav_numbers = re.findall(r'\d+', fav_text)
                if fav_numbers:
                    try:
                        entry_data['favorite_count'] = int(fav_numbers[0])
                    except ValueError:
                        entry_data['favorite_count'] = 0
                else:
                    entry_data['favorite_count'] = 0
            
            # Entry numarası (sıralama)
            entry_no_elem = (entry_element.find('span', {'class': 'index'}) or
                           entry_element.find('span', class_=re.compile('index')) or
                           entry_element.find('span', class_=re.compile('entry.*number')))
            if entry_no_elem:
                entry_data['entry_number'] = entry_no_elem.get_text(strip=True)
            
            # Entry ID ve content zorunlu
            if 'entry_id' in entry_data and 'content' in entry_data and entry_data['content']:
                return entry_data
            
        except Exception as e:
            print(f"Uyarı: Entry ayrıştırma hatası: {e}", file=sys.stderr)
        
        return None
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Ekşi Sözlük tarih formatını parse eder"""
        try:
            # Formatlar: "12.01.2024 15:30" veya "dün 15:30" veya "bugün 15:30" veya "20.02.1999 ~ 06.05.2007 01:16"
            date_str = date_str.strip()
            
            # Tarih aralığı formatı: "26.10.2025 15:42 ~ 18:12" veya "20.02.1999 ~ 06.05.2007 01:16"
            # İlk tarihi kullan (orijinal posting tarihi)
            if ' ~ ' in date_str:
                # İlk kısmı al (orijinal tarih)
                first_part = date_str.split(' ~ ')[0].strip()
                # Eğer ilk kısımda tam tarih varsa onu kullan
                date_pattern_with_time = r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})'
                match = re.match(date_pattern_with_time, first_part)
                if match:
                    day, month, year, hour, minute = map(int, match.groups())
                    return datetime(year, month, day, hour, minute)
                # Sadece tarih varsa
                date_pattern_date_only = r'(\d{1,2})\.(\d{1,2})\.(\d{4})'
                match = re.match(date_pattern_date_only, first_part)
                if match:
                    day, month, year = map(int, match.groups())
                    return datetime(year, month, day)
                # Eğer ilk kısım parse edilemezse, ikinci kısmı dene
                second_part = date_str.split(' ~ ')[-1].strip()
                date_str = second_part
            
            # Bugün/dün kontrolü
            if date_str.startswith('bugün'):
                today = datetime.now()
                time_part = re.search(r'(\d{1,2}):(\d{2})', date_str)
                if time_part:
                    hour, minute = int(time_part.group(1)), int(time_part.group(2))
                    return today.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return datetime.now()
            
            if date_str.startswith('dün'):
                yesterday = datetime.now() - timedelta(days=1)
                time_part = re.search(r'(\d{1,2}):(\d{2})', date_str)
                if time_part:
                    hour, minute = int(time_part.group(1)), int(time_part.group(2))
                    return yesterday.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return datetime.now() - timedelta(days=1)
            
            # Normal tarih formatı: DD.MM.YYYY HH:MM
            date_pattern = r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})'
            match = re.match(date_pattern, date_str)
            if match:
                day, month, year, hour, minute = map(int, match.groups())
                return datetime(year, month, day, hour, minute)
            
            # Sadece tarih: DD.MM.YYYY
            date_pattern = r'(\d{1,2})\.(\d{1,2})\.(\d{4})'
            match = re.match(date_pattern, date_str)
            if match:
                day, month, year = map(int, match.groups())
                return datetime(year, month, day)
            
        except Exception as e:
            print(f"Uyarı: Tarih ayrıştırma hatası: {date_str} - {e}", file=sys.stderr)
        
        return None
    
    def _find_last_page(self, soup: BeautifulSoup, title: str, title_id: Optional[str] = None, pagination_format: Optional[str] = None) -> Optional[int]:
        """Son sayfa numarasını pagination linklerinden bulur"""
        try:
            # Pagination linklerini kontrol et
            pagination_links = soup.find_all('a', href=re.compile(r'p=\d+'))
            
            max_page_from_links = 1
            for link in pagination_links:
                href = link.get('href', '')
                page_match = re.search(r'p=(\d+)', href)
                if page_match:
                    page_num = int(page_match.group(1))
                    max_page_from_links = max(max_page_from_links, page_num)
            
            # Eğer pagination linklerinden sayfa bulduysak, onu döndür
            if max_page_from_links > 1:
                return max_page_from_links
            
            return None
        except Exception as e:
            print(f"Uyarı: Son sayfa bulunamadı: {e}", file=sys.stderr)
            return None
    
    def _fetch_entry_by_id(self, entry_id: str) -> Optional[Dict]:
        """Belirli bir entry ID'si ile entry'yi fetch eder"""
        # Entry URL'i oluştur
        entry_url = f"{self.BASE_URL}/entry/{entry_id}"
        
        response = self._make_request(entry_url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Entry'yi bul - entry sayfasında genellikle tek bir entry var
        entry_elements = soup.find_all('li', {'data-id': entry_id})
        
        if not entry_elements:
            entry_elements = soup.select(f'li[data-id="{entry_id}"]')
        
        if not entry_elements:
            # Entry container'ından ara
            entry_list = (soup.find('ul', id='entry-item-list') or 
                        soup.find('ul', id='entry-list'))
            if entry_list:
                entry_elements = entry_list.find_all('li', {'data-id': entry_id})
        
        if entry_elements:
            entry = self._parse_entry(entry_elements[0])
            if entry:
                # Topic bilgisini sayfadan çıkar
                h1_title = soup.find('h1')
                if h1_title:
                    title_link = h1_title.find('a', href=True)
                    if title_link and title_link.get('href'):
                        topic_href = title_link['href']
                        topic_match = re.search(r'/([^/]+)--(\d+)', topic_href)
                        if topic_match:
                            entry['title'] = topic_match.group(1)
                
                return entry
        
        return None
    
    def _fetch_referenced_entries(self, entries: List[Dict]) -> Dict[str, List[Dict]]:
        """Entry'lerdeki referans edilen entry'leri fetch eder ve entry ID'ye göre gruplar
        
        Returns:
            Dict mapping entry_id to list of referenced entries
        """
        referenced_entries_map = {}  # entry_id -> list of referenced entries
        entries_to_fetch = {}  # ref_entry_id -> list of parent entry_ids that reference it
        main_entries_dict = {e.get('entry_id'): e for e in entries if e.get('entry_id')}  # entry_id -> entry dict for quick lookup
        
        # Tüm referans edilen entry ID'lerini topla ve hangi entry'lerin referans verdiğini kaydet
        for entry in entries:
            entry_id = entry.get('entry_id')
            if not entry_id:
                continue
                
            ref_ids = entry.get('referenced_entry_ids', [])
            for ref_id in ref_ids:
                # Her referans için parent entry'yi kaydet
                if entry_id not in referenced_entries_map:
                    referenced_entries_map[entry_id] = []
                
                # Eğer referans edilen entry zaten main list'te varsa, onu kullan
                if ref_id in main_entries_dict:
                    # Main list'teki entry'nin bir kopyasını ekle
                    referenced_entry_copy = main_entries_dict[ref_id].copy()
                    referenced_entries_map[entry_id].append(referenced_entry_copy)
                # Eğer daha önce scrape edilmediyse fetch et
                elif ref_id not in self.scraped_entry_ids:
                    if ref_id not in entries_to_fetch:
                        entries_to_fetch[ref_id] = []
                    entries_to_fetch[ref_id].append(entry_id)
        
        # Referans edilen entry'leri fetch et (sadece main list'te olmayanlar)
        for ref_entry_id, parent_entry_ids in entries_to_fetch.items():
            print(f"Referans edilen entry alınıyor: {ref_entry_id}", file=sys.stderr)
            referenced_entry = self._fetch_entry_by_id(ref_entry_id)
            if referenced_entry:
                # Entry ID'yi işaretle
                self.scraped_entry_ids.add(ref_entry_id)
                
                # Her parent entry için bu referans edilen entry'yi ekle
                for parent_entry_id in parent_entry_ids:
                    if parent_entry_id not in referenced_entries_map:
                        referenced_entries_map[parent_entry_id] = []
                    # Referans edilen entry'nin bir kopyasını ekle
                    referenced_entry_copy = referenced_entry.copy()
                    referenced_entries_map[parent_entry_id].append(referenced_entry_copy)
                
                time.sleep(self.delay)  # Rate limiting
        
        return referenced_entries_map
    
    def _find_last_page_from_pagination(self, soup: BeautifulSoup) -> Optional[int]:
        """İlk sayfadaki pagination'dan son sayfa numarasını bulur"""
        try:
            # Öncelikle data-pagecount attribute'undan al
            pagination_div = soup.find('div', class_='pager')
            if pagination_div and pagination_div.get('data-pagecount'):
                try:
                    pagecount = int(pagination_div.get('data-pagecount'))
                    if pagecount > 0:
                        return pagecount
                except (ValueError, TypeError):
                    pass
            
            # Fallback: pagination linklerinden bul
            pagination_links = soup.find_all('a', href=re.compile(r'p=\d+'))
            max_page = 1
            for link in pagination_links:
                href = link.get('href', '')
                page_match = re.search(r'p=(\d+)', href)
                if page_match:
                    page_num = int(page_match.group(1))
                    max_page = max(max_page, page_num)
            
            # Sayfa numaralarını içeren text içinde de ara
            pagination_text = soup.get_text()
            page_matches = re.findall(r'\b(\d+)\s*(?:sayfa|page)', pagination_text, re.I)
            for match in page_matches:
                try:
                    page_num = int(match)
                    max_page = max(max_page, page_num)
                except ValueError:
                    pass
            
            return max_page if max_page > 1 else None
        except Exception as e:
            print(f"Uyarı: Son sayfa bulunamadı: {e}", file=sys.stderr)
            return None
    
    def _sort_entries_by_date(self, entries: List[Dict]) -> List[Dict]:
        """Entry'leri tarihe göre sıralar (en eski önce)"""
        sorted_entries = entries.copy()
        sorted_entries.sort(key=lambda e: self._parse_datetime(e.get('date', '')) or datetime.min, reverse=False)
        return sorted_entries
    
    def _detect_format_from_filename(self, filename: str) -> str:
        """Dosya adından format tespit eder (csv, markdown, json)"""
        if not filename:
            return 'json'
        
        filename_lower = filename.lower()
        if filename_lower.endswith('.csv'):
            return 'csv'
        elif filename_lower.endswith(('.md', '.markdown')):
            return 'markdown'
        else:
            return 'json'
    
    def _write_json(self, entries: List[Dict]):
        """Entry'leri JSON formatında yazar"""
        output_data = {
            'scrape_info': {
                'timestamp': (self.scrape_start_time or datetime.now()).isoformat(),
                'total_entries': len(entries),
                'input': self.scrape_input or '',
                'time_filter': self.scrape_time_filter
            },
            'entries': entries
        }
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    def _write_csv(self, entries: List[Dict]):
        """Entry'leri CSV formatında yazar"""
        with open(self.output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            # Scrape info'yu yorum olarak yaz
            scrape_info = {
                'timestamp': (self.scrape_start_time or datetime.now()).isoformat(),
                'total_entries': len(entries),
                'input': self.scrape_input or '',
                'time_filter': self.scrape_time_filter
            }
            f.write(f"# Scrape Info: {json.dumps(scrape_info, ensure_ascii=False)}\n")
            
            # CSV başlıkları
            headers = ['entry_id', 'title', 'date', 'author', 'content', 'referenced_content']
            writer.writerow(headers)
            
            # Entry'leri yaz
            for entry in entries:
                # referenced_content'i JSON string olarak serialize et
                referenced_content = entry.get('referenced_content', [])
                referenced_content_str = json.dumps(referenced_content, ensure_ascii=False) if referenced_content else ''
                
                row = [
                    entry.get('entry_id', ''),
                    entry.get('title', ''),
                    entry.get('date', ''),
                    entry.get('author', ''),
                    entry.get('content', ''),
                    referenced_content_str
                ]
                writer.writerow(row)
    
    def _write_markdown(self, entries: List[Dict]):
        """Entry'leri Markdown formatında yazar"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            # Scrape info'yu markdown section olarak yaz
            f.write("# Ekşi Sözlük Scrape Results\n\n")
            f.write("## Scrape Info\n\n")
            scrape_info = {
                'timestamp': (self.scrape_start_time or datetime.now()).isoformat(),
                'total_entries': len(entries),
                'input': self.scrape_input or '',
                'time_filter': self.scrape_time_filter
            }
            f.write(f"- **Timestamp**: {scrape_info['timestamp']}\n")
            f.write(f"- **Total Entries**: {scrape_info['total_entries']}\n")
            f.write(f"- **Input**: {scrape_info['input']}\n")
            if scrape_info['time_filter']:
                f.write(f"- **Time Filter**: {scrape_info['time_filter']}\n")
            f.write("\n")
            
            # Entry'leri yaz
            f.write("## Entries\n\n")
            for i, entry in enumerate(entries, 1):
                entry_id = entry.get('entry_id', '')
                title = entry.get('title', '')
                date = entry.get('date', '')
                author = entry.get('author', '')
                content = entry.get('content', '')
                referenced_content = entry.get('referenced_content', [])
                
                # Entry başlığı
                f.write(f"### Entry {i}")
                if entry_id:
                    f.write(f" (ID: {entry_id})")
                f.write("\n\n")
                
                # Entry bilgileri
                if title:
                    f.write(f"**Title**: {title}\n\n")
                if date:
                    f.write(f"**Date**: {date}\n\n")
                if author:
                    f.write(f"**Author**: {author}\n\n")
                
                # Entry içeriği
                if content:
                    f.write("**Content**:\n\n")
                    # İçeriği code block veya normal paragraf olarak yaz
                    f.write(f"{content}\n\n")
                
                # Referenced content (bkz linkleri)
                if referenced_content:
                    f.write("**Referenced Content**:\n\n")
                    for ref_idx, ref_entry in enumerate(referenced_content, 1):
                        ref_entry_id = ref_entry.get('entry_id', '')
                        ref_title = ref_entry.get('title', '')
                        ref_date = ref_entry.get('date', '')
                        ref_author = ref_entry.get('author', '')
                        ref_content = ref_entry.get('content', '')
                        
                        f.write(f"#### Referenced Entry {ref_idx}")
                        if ref_entry_id:
                            f.write(f" (ID: {ref_entry_id})")
                        f.write("\n\n")
                        
                        if ref_title:
                            f.write(f"- **Title**: {ref_title}\n")
                        if ref_date:
                            f.write(f"- **Date**: {ref_date}\n")
                        if ref_author:
                            f.write(f"- **Author**: {ref_author}\n")
                        if ref_content:
                            f.write(f"- **Content**: {ref_content}\n")
                        f.write("\n")
                
                # Entry'ler arası ayırıcı
                if i < len(entries):
                    f.write("---\n\n")
    
    def _write_entries_to_file(self, entries: List[Dict]):
        """Entry'leri dosyaya yazar, format dosya uzantısına göre otomatik tespit edilir"""
        # Mevcut entry'leri her zaman güncelle (Ctrl+C için gerekli)
        self.current_entries = entries
        
        # Dosya yazma işlemi sadece output_file varsa yapılır
        if not self.output_file:
            return
        
        try:
            # Format'ı dosya uzantısından tespit et
            output_format = self._detect_format_from_filename(self.output_file)
            
            # Format'a göre ilgili formatter'ı çağır
            if output_format == 'csv':
                self._write_csv(entries)
            elif output_format == 'markdown':
                self._write_markdown(entries)
            else:  # json (default)
                self._write_json(entries)
        
        except Exception as e:
            print(f"Uyarı: Entry'ler dosyaya yazılamadı: {e}", file=sys.stderr)
    
    def scrape_title(self, title: str, time_filter: Optional[timedelta] = None, time_filter_string: Optional[str] = None) -> List[Dict]:
        """Bir başlıktaki tüm entry'leri scrape eder"""
        # Scrape bilgilerini kaydet
        self.scrape_start_time = datetime.now()
        self.scrape_input = title
        # Zaman filtresi string'ini Türkçeleştir
        if time_filter_string:
            # İngilizce string'i Türkçeleştir
            if 'months' in time_filter_string:
                months_num = time_filter_string.split()[0]
                self.scrape_time_filter = f"{months_num} ay"
            elif 'weeks' in time_filter_string:
                weeks_num = time_filter_string.split()[0]
                self.scrape_time_filter = f"{weeks_num} hafta"
            elif 'days' in time_filter_string:
                days_num = time_filter_string.split()[0]
                self.scrape_time_filter = f"{days_num} gün"
            elif 'years' in time_filter_string:
                years_num = time_filter_string.split()[0]
                self.scrape_time_filter = f"{years_num} yıl"
            else:
                self.scrape_time_filter = time_filter_string
        elif time_filter:
            days = time_filter.days
            if days >= 365:
                years = days // 365
                self.scrape_time_filter = f"{years} yıl"
            elif days >= 30:
                months = days // 30
                self.scrape_time_filter = f"{months} ay"
            elif days >= 7:
                weeks = days // 7
                self.scrape_time_filter = f"{weeks} hafta"
            else:
                self.scrape_time_filter = f"{days} gün"
        else:
            self.scrape_time_filter = None
        
        entries = []
        page = 1
        title_id = None  # Topic ID'yi saklamak için
        title_slug = None  # Slug'ı saklamak için
        pagination_format = None  # Pagination URL formatını sakla
        
        print(f"Başlık taranıyor: {title}", file=sys.stderr)
        
        # Eğer zaman filtresi varsa, son sayfadan başlayıp geriye doğru gideceğiz
        reverse_order = False
        last_page = None  # Son sayfa numarası
        
        while True:
            # Başlık URL'i oluştur
            if page == 1:
                url = f"{self.BASE_URL}/{title}"
            else:
                # Doğru pagination formatını kullan
                if pagination_format:
                    url = f"{self.BASE_URL}{pagination_format.format(page=page)}"
                elif title_id:
                    url = f"{self.BASE_URL}/{title}--{title_id}?p={page}"
                else:
                    url = f"{self.BASE_URL}/{title}?p={page}"
            
            # URL'i logla
            print(f"Sayfaya bakılıyor: {url}", file=sys.stderr)
            
            response = self._make_request(url)
            if not response:
                # 404 veya başka bir hata - sayfa yok veya erişilemiyor
                if page > 1:
                    print(f"Sayfa {page} bulunamadı, tarama sonlandırılıyor", file=sys.stderr)
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # İlk sayfada topic ID ve pagination formatını çıkar
            if page == 1 and not title_id:
                response_url = response.url
                # URL formatı: https://eksisozluk.com/kis-gunesi--46338 veya https://eksisozluk.com/kis-gunesi--46338?p=1
                # URL'den güncellenmiş slug'ı ve topic ID'yi çıkar
                # Önce query string'i temizle
                parsed_response_url = urlparse(response_url)
                clean_path = parsed_response_url.path.strip('/')
                normalized_slug = None  # Güncellenmiş slug'ı saklamak için
                
                # Path formatı: kis-gunesi--46338
                if '--' in clean_path:
                    parts = clean_path.split('--')
                    if len(parts) == 2:
                        normalized_slug = parts[0]  # kis-gunesi
                        title_id = parts[1]  # 46338
                        print(f"Başlık kimliği bulundu: {title_id}", file=sys.stderr)
                        print(f"Güncellenmiş başlık adresi bulundu: {normalized_slug}", file=sys.stderr)
                    else:
                        # Alternatif: URL'de -- ile başlayan sayı ara
                        alt_match = re.search(r'--(\d+)', response_url)
                        if alt_match:
                            title_id = alt_match.group(1)
                            # Slug'ı manuel olarak çıkar
                            slug_match = re.search(r'([^/]+)--\d+', clean_path)
                            if slug_match:
                                normalized_slug = slug_match.group(1)
                            else:
                                normalized_slug = title  # Fallback olarak orijinal title kullan
                            print(f"Başlık kimliği bulundu (alternatif yöntem): {title_id}", file=sys.stderr)
                else:
                    # Alternatif: URL'de -- ile başlayan sayı ara
                    alt_match = re.search(r'--(\d+)', response_url)
                    if alt_match:
                        title_id = alt_match.group(1)
                        # Slug'ı path'ten çıkar
                        slug_match = re.search(r'/([^/]+)--\d+', parsed_response_url.path)
                        if slug_match:
                            normalized_slug = slug_match.group(1)
                        else:
                            normalized_slug = title  # Fallback olarak orijinal title kullan
                        print(f"INFO: Topic ID bulundu (alternatif yöntem): {title_id}", file=sys.stderr)
                
                # Basit format: /normalized-slug--id?p=X kullan (güncellenmiş URL'den alınan slug ile)
                # Pagination linklerindeki /basliklar/gundem formatı yanlış sonuçlara yol açıyor
                if title_id:
                    if normalized_slug:
                        pagination_format = f"/{normalized_slug}--{title_id}?p={{page}}"
                        print(f"Sayfa numaralandırma formatı bulundu: {pagination_format}", file=sys.stderr)
                    else:
                        # Fallback: Orijinal title kullan (normalized_slug bulunamadıysa)
                        pagination_format = f"/{title}--{title_id}?p={{page}}"
                        print(f"Sayfa numaralandırma formatı bulundu (yedek yöntem): {pagination_format}", file=sys.stderr)
                else:
                    # Son çare: pagination linklerinden formatı çıkar
                    pagination_link = soup.find('a', href=re.compile(r'p=\d+'))
                    if pagination_link and pagination_link.get('href'):
                        href = pagination_link['href']
                        parsed_url = urlparse(href)
                        params = parse_qs(parsed_url.query)
                        
                        if 'id' in params and 'slug' in params:
                            title_id = params['id'][0]
                            title_slug = params['slug'][0]
                            pagination_format = f"{parsed_url.path}?p={{page}}&id={title_id}&slug={title_slug}"
                            print(f"Sayfa numaralandırma formatı bulundu: {pagination_format}", file=sys.stderr)
            
            # İlk sayfada pagination'dan son sayfa numarasını bul
            if page == 1 and not last_page:
                last_page = self._find_last_page_from_pagination(soup)
                
                if last_page:
                    print(f"Son sayfa numarası: {last_page}", file=sys.stderr)
                    
                    # Zaman filtresi varsa son sayfadan başla
                    if time_filter:
                        page = last_page
                        reverse_order = True
                        print(f"Son sayfadan başlayıp geriye doğru taranıyor (sayfa {last_page}'den başlıyor)", file=sys.stderr)
                        # İlk sayfayı atla, direkt son sayfaya git
                        continue
                else:
                    print(f"Uyarı: Son sayfa bulunamadı", file=sys.stderr)
            
            # Entry'leri bul - çoklu selector stratejisi (önce entry'leri bul, sonra kontrol et)
            # ÖNEMLİ: Ekşi Sözlük'te entry'ler ul#entry-item-list içinde
            entry_elements = soup.find_all('li', {'data-id': True})
            
            # Önce doğru container'ı bul
            if not entry_elements:
                entry_elements = soup.select('ul#entry-item-list > li')
            
            if not entry_elements:
                entry_elements = soup.select('ul#entry-list > li')
            
            if not entry_elements:
                # entry-item-list veya entry-list container'ını bul
                entry_list = (soup.find('ul', id='entry-item-list') or 
                            soup.find('ul', id='entry-list') or 
                            soup.find('ul', class_=re.compile('entry.*list')))
                if entry_list:
                    entry_elements = entry_list.find_all('li', {'data-id': True})
            
            if not entry_elements:
                entry_elements = soup.find_all('li', class_=re.compile('entry'))
            
            if not entry_elements:
                entry_elements = soup.find_all('div', {'class': 'content-item'})
            
            if not entry_elements:
                print(f"Sayfa {page}'de entry bulunamadı, tarama sonlandırılıyor", file=sys.stderr)
                break
            
            page_entries = []
            all_entries_too_old = True
            
            for elem in entry_elements:
                entry = self._parse_entry(elem)
                if entry:
                    entry_id = entry.get('entry_id')
                    # Entry ID'yi işaretle (duplikasyon önleme)
                    if entry_id:
                        self.scraped_entry_ids.add(entry_id)
                    
                    # Zaman filtresi kontrolü
                    if time_filter:
                        entry_dt = self._parse_datetime(entry.get('date', ''))
                        if not entry_dt:
                            # Tarih parse edilemezse, zaman filtresi aktifken entry'yi dahil etme
                            # (güvenli tarafta kal: parse edilemeyen tarihleri hariç tut)
                            continue
                        
                        # Entry'nin zaman filtresi içinde olup olmadığını kontrol et
                        entry_age = datetime.now() - entry_dt
                        if entry_age <= time_filter:
                            # Zaman filtresi içinde, ekle
                            entry['title'] = title
                            page_entries.append(entry)
                            all_entries_too_old = False
                        # Eğer entry çok eskiyse, sadece skip et (durma)
                    else:
                        # Zaman filtresi yok, tüm entry'leri ekle
                        entry['title'] = title
                        page_entries.append(entry)
                        all_entries_too_old = False
            
            entries.extend(page_entries)
            print(f"Sayfa {page} tamamlandı, {len(page_entries)} entry bulundu (şu ana kadar toplam: {len(entries)})", file=sys.stderr)
            
            # Max entries kontrolü
            if self.max_entries and len(entries) >= self.max_entries:
                # Limit aşıldı, fazla entry'leri kaldır
                entries = entries[:self.max_entries]
                print(f"Maksimum entry sayısına ulaşıldı ({self.max_entries}), tarama durduruluyor", file=sys.stderr)
                # Entry'leri dosyaya yaz (incremental update)
                self._write_entries_to_file(entries)
                break
            
            # Entry'leri dosyaya yaz (incremental update)
            self._write_entries_to_file(entries)
            
            # Eğer zaman filtresi varsa ve bu sayfadaki TÜM entry'ler belirtilen süreyi aşmışsa dur
            if time_filter and all_entries_too_old:
                if entry_elements:
                    # Sayfada entry var ama hepsi çok eski
                    filter_display = self.scrape_time_filter or f"{time_filter.days} gün"
                    # İngilizce time filter string'i Türkçeleştir
                    if filter_display:
                        if 'months' in filter_display:
                            months_num = filter_display.split()[0]
                            filter_display = f"{months_num} ay"
                        elif 'weeks' in filter_display:
                            weeks_num = filter_display.split()[0]
                            filter_display = f"{weeks_num} hafta"
                        elif 'days' in filter_display:
                            days_num = filter_display.split()[0]
                            filter_display = f"{days_num} gün"
                        elif 'years' in filter_display:
                            years_num = filter_display.split()[0]
                            filter_display = f"{years_num} yıl"
                    print(f"Bu sayfadaki entry'ler çok eskiymiş ({filter_display} süresini aşmış), tarama durduruldu", file=sys.stderr)
                    break
                else:
                    # Sayfada entry yok, bir sonraki sayfaya geç
                    pass
            
            # Sayfa navigasyonu
            if reverse_order:
                # Ters sırada: önceki sayfaya git
                page -= 1
                if page < 1:
                    break
            else:
                # Normal sırada: sonraki sayfaya git
                # Eğer bu sayfada entry yoksa dur (zaman filtresi yoksa)
                if not page_entries and not time_filter:
                    break
                
                # Son sayfa numarasından fazla gidebiliyor muyuz kontrol et
                if last_page and page >= last_page:
                    print(f"Son sayfa numarasına ulaşıldı ({last_page}), tarama sonlandırılıyor", file=sys.stderr)
                    break
                
                # Bir sonraki sayfaya geç
                page += 1
            
            time.sleep(self.delay)
        
        # Referans edilen entry'leri fetch et ve ilgili entry'lere ekle
        if self.fetch_referenced:
            print(f"Referans edilen entry'ler kontrol ediliyor, biraz bekleyin...", file=sys.stderr)
            referenced_entries_map = self._fetch_referenced_entries(entries)
            if referenced_entries_map:
                total_referenced = 0
                # Her entry'yi kontrol et ve referans edilen entry'leri ekle
                for entry in entries:
                    entry_id = entry.get('entry_id')
                    if entry_id in referenced_entries_map:
                        entry['referenced_content'] = referenced_entries_map[entry_id]
                        total_referenced += len(referenced_entries_map[entry_id])
                print(f"{total_referenced} referans edilen entry eklendi", file=sys.stderr)
                # Entry'leri dosyaya yaz (güncellenmiş liste ile)
                self._write_entries_to_file(entries)
        
        # referenced_entry_ids alanını tüm entry'lerden kaldır (sadece iç kullanım içindi)
        for entry in entries:
            entry.pop('referenced_entry_ids', None)
        
        # Eğer son sayfadan başlanarak alındıysa ve output dosyası belirtilmişse, entry'leri tarihe göre sırala
        if reverse_order and self.output_file:
            print(f"Entry'ler tarihe göre sıralanıyor, biraz bekleyin...", file=sys.stderr)
            entries.sort(key=lambda e: self._parse_datetime(e.get('date', '')) or datetime.min, reverse=False)
            # Sıralanmış entry'leri dosyaya yaz
            self._write_entries_to_file(entries)
            print(f"Entry'ler tarihe göre sıralandı ve dosyaya yazıldı, işlem tamamlandı", file=sys.stderr)
        
        return entries
    
    def scrape_entry_and_following(self, entry_url: str) -> List[Dict]:
        """Belirli bir entry'den başlayarak sonraki entry'leri scrape eder"""
        # Scrape bilgilerini kaydet
        self.scrape_start_time = datetime.now()
        self.scrape_input = entry_url
        self.scrape_time_filter = None
        
        entries = []
        
        # Entry URL'inden entry ID'yi çıkar
        parsed_url = urlparse(entry_url)
        path = parsed_url.path.strip('/')
        
        # İki format destekleniyor:
        # 1. /entry/{id} formatı (yeni format)
        # 2. /{title}--{id} formatı (eski format)
        entry_id = None
        title = None
        title_id = None
        
        # /entry/{id} formatını kontrol et
        entry_match = re.match(r'entry/(\d+)', path)
        if entry_match:
            entry_id = entry_match.group(1)
            print(f"Entry URL formatı tespit edildi: /entry/{entry_id}", file=sys.stderr)
            
            # Entry sayfasını fetch et
            response = self._make_request(entry_url)
            if not response:
                print(f"Hata: Entry sayfası yüklenemedi: {entry_url}", file=sys.stderr)
                return entries
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Topic bilgisini entry sayfasından çıkar
            # Öncelikle h1 içindeki başlık linkine bak
            h1_title = soup.find('h1')
            if h1_title:
                title_link = h1_title.find('a', href=True)
                if title_link and title_link.get('href'):
                    topic_href = title_link['href']
                    # Topic URL formatı: /title--id veya /title--id?p=X
                    topic_match = re.search(r'/([^/]+)--(\d+)', topic_href)
                    if topic_match:
                        title = topic_match.group(1)
                        title_id = topic_match.group(2)
                        print(f"Başlık bulundu (h1 link): {title} (ID: {title_id})", file=sys.stderr)
            
            # Eğer bulunamadıysa, sayfa title'ından çıkar
            if not title:
                page_title = soup.find('title')
                if page_title:
                    title_text = page_title.get_text()
                    # Format: "galatasaray - #179413362 - ekşi sözlük"
                    title_match = re.match(r'([^-\#]+)', title_text.strip())
                    if title_match:
                        potential_title = title_match.group(1).strip()
                        # Topic sayfasına gidip title ID'yi al
                        test_url = f"{self.BASE_URL}/{potential_title}"
                        test_response = self._make_request(test_url)
                        if test_response:
                            test_url_parsed = urlparse(test_response.url)
                            test_path = test_url_parsed.path
                            test_match = re.search(r'/([^/]+)--(\d+)', test_path)
                            if test_match:
                                title = test_match.group(1)
                                title_id = test_match.group(2)
                                print(f"Başlık bulundu (sayfa başlığından): {title} (ID: {title_id})", file=sys.stderr)
            
            # Hala bulunamadıysa, genel link arama
            if not title:
                topic_link = soup.find('a', href=re.compile(r'/[^/]+--\d+')) or \
                            soup.find('a', href=re.compile(r'/[^/]+--\d+\?p=\d+'))
                
                if topic_link and topic_link.get('href'):
                    topic_href = topic_link['href']
                    # Topic URL formatı: /title--id veya /title--id?p=X
                    topic_match = re.search(r'/([^/]+)--(\d+)', topic_href)
                    if topic_match:
                        title = topic_match.group(1)
                        title_id = topic_match.group(2)
                        print(f"Başlık bulundu: {title} (ID: {title_id})", file=sys.stderr)
            
            # Eğer topic linkinden bulunamazsa, meta tag veya diğer elementlerden dene
            if not title:
                # Meta tag'lerden dene
                meta_title = soup.find('meta', property='og:title')
                if meta_title and meta_title.get('content'):
                    # Meta title'dan topic çıkarılabilir
                    pass
                
                # Alternatif: Sayfa başlığından veya breadcrumb'dan
                breadcrumb = soup.find('nav', class_=re.compile('breadcrumb')) or \
                           soup.find('div', class_=re.compile('breadcrumb'))
                if breadcrumb:
                    breadcrumb_links = breadcrumb.find_all('a')
                    for link in breadcrumb_links:
                        href = link.get('href', '')
                        topic_match = re.search(r'/([^/]+)--(\d+)', href)
                        if topic_match:
                            title = topic_match.group(1)
                            title_id = topic_match.group(2)
                            print(f"Başlık bulundu (breadcrumb): {title} (ID: {title_id})", file=sys.stderr)
                            break
            
            # Hala bulunamazsa, topic sayfasına focusto ile yönlendir
            if not title:
                # Entry sayfasında "X entry daha" butonunu bul ve tıkla
                # Veya direkt topic sayfasına focusto parametresi ile git
                # Önce entry ID'den topic bilgisini çıkarmayı dene
                # Alternatif: Entry sayfasından topic slug'ını çıkar
                entry_content = soup.find('div', class_=re.compile('content')) or \
                              soup.find('article') or \
                              soup.find('div', id='entry-item-list')
                
                # Entry sayfasında genellikle topic linki var
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    # Topic URL formatını kontrol et
                    if '--' in href and re.match(r'/[^/]+--\d+', href):
                        topic_match = re.search(r'/([^/]+)--(\d+)', href)
                        if topic_match:
                            title = topic_match.group(1)
                            title_id = topic_match.group(2)
                            print(f"Başlık bulundu (sayfa linklerinden): {title} (ID: {title_id})", file=sys.stderr)
                            break
            
            if not title or not title_id:
                print(f"Hata: Entry sayfasından başlık bilgisi çıkarılamadı: {entry_url}", file=sys.stderr)
                return entries
            
            # Topic sayfasına focusto parametresi ile git
            topic_url = f"{self.BASE_URL}/{title}--{title_id}?focusto={entry_id}"
            print(f"Başlık sayfasına yönlendiriliyor: {topic_url}", file=sys.stderr)
            
            response = self._make_request(topic_url)
            if not response:
                print(f"Hata: Başlık sayfası yüklenemedi: {topic_url}", file=sys.stderr)
                return entries
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Mevcut sayfa numarasını pagination'dan çıkar
            current_page = 1
            response_url = response.url
            
            # Öncelikle URL'den sayfa numarasını çıkar (redirect sonrası URL'de p= olabilir)
            url_page_match = re.search(r'[?&]p=(\d+)', response_url)
            if url_page_match:
                current_page = int(url_page_match.group(1))
                print(f"Entry'nin bulunduğu sayfa (URL'den): {current_page}", file=sys.stderr)
            else:
                # URL'de yoksa, pagination div'inden bul
                pagination_div = soup.find('div', class_='pager')
                if pagination_div:
                    # data-currentpage attribute'u varsa onu kullan
                    if pagination_div.get('data-currentpage'):
                        try:
                            current_page = int(pagination_div.get('data-currentpage'))
                            print(f"Entry'nin bulunduğu sayfa (data-currentpage): {current_page}", file=sys.stderr)
                        except (ValueError, TypeError):
                            pass
                    
                    # Eğer hala bulunamadıysa, sayfa numarası text'inden bul
                    if current_page == 1:
                        # Sayfa numarası genellikle pager içinde gösterilir
                        # Format: "6804 / 6824" veya sadece "6804"
                        page_text = pagination_div.get_text()
                        # Sayfa numarasını bul - "6804 / 6824" formatı (en yaygın format)
                        # Önce "X / Y" formatını ara, X mevcut sayfa, Y toplam sayfa
                        page_match = re.search(r'(\d+)\s*/\s*(\d+)', page_text)
                        if page_match:
                            current_page = int(page_match.group(1))
                            print(f"Entry'nin bulunduğu sayfa (pager text): {current_page}", file=sys.stderr)
                        else:
                            # Alternatif: Pagination butonlarını kontrol et
                            page_buttons = pagination_div.find_all(['button', 'a', 'span', 'div'])
                            for button in page_buttons:
                                button_text = button.get_text(strip=True)
                                # "6804 / 6824" formatını kontrol et
                                btn_match = re.search(r'(\d+)\s*/\s*(\d+)', button_text)
                                if btn_match:
                                    current_page = int(btn_match.group(1))
                                    print(f"Entry'nin bulunduğu sayfa (button text): {current_page}", file=sys.stderr)
                                    break
                                
                                # Sadece sayı varsa ve aktif sınıfı varsa bu sayfa numarası
                                button_classes = button.get('class', [])
                                is_active = any(cls in ['active', 'current', 'selected'] for cls in button_classes) if button_classes else False
                                if button_text.isdigit() and is_active:
                                    # Ancak küçük sayılar (1-10) genellikle sayfa numarası değil, sayfa butonu
                                    # Sadece büyük sayılar (> 100) sayfa numarası olabilir
                                    page_num = int(button_text)
                                    if page_num > 100:  # Büyük sayılar sayfa numarası olabilir
                                        current_page = page_num
                                        print(f"Entry'nin bulunduğu sayfa (active button, büyük sayı): {current_page}", file=sys.stderr)
                                        break
                            
                            # Hala bulunamadıysa, aktif sayfa linkini bul
                            if current_page == 1:
                                active_page = pagination_div.find('a', class_=re.compile('active|current|selected'))
                                if active_page:
                                    href = active_page.get('href', '')
                                    page_match = re.search(r'p=(\d+)', href)
                                    if page_match:
                                        current_page = int(page_match.group(1))
                                        print(f"Entry'nin bulunduğu sayfa (active link): {current_page}", file=sys.stderr)
                            
                            # Son çare: Pagination div'inde tüm sayıları bul ve "X / Y" formatını ara
                            # Tüm pagination içeriğini tekrar kontrol et
                            if current_page == 1:
                                # Pagination div'inin tüm HTML'ini kontrol et
                                pagination_html = str(pagination_div)
                                # "X / Y" formatını HTML içinde ara
                                html_page_match = re.search(r'(\d+)\s*/\s*(\d+)', pagination_html)
                                if html_page_match:
                                    current_page = int(html_page_match.group(1))
                                    print(f"Entry'nin bulunduğu sayfa (pagination HTML): {current_page}", file=sys.stderr)
                else:
                    # Pagination div bulunamadı
                    print(f"Uyarı: Sayfa numaralandırma div'i bulunamadı, sayfa numarası varsayılan olarak 1 kullanılıyor", file=sys.stderr)
            
            # Bu sayfadaki entry'leri bul ve entry'den itibaren al
            entry_elements = soup.find_all('li', {'data-id': True})
            
            if not entry_elements:
                entry_elements = soup.select('ul#entry-item-list > li')
            
            if not entry_elements:
                entry_elements = soup.select('ul#entry-list > li')
            
            if not entry_elements:
                entry_list = (soup.find('ul', id='entry-item-list') or 
                            soup.find('ul', id='entry-list'))
                if entry_list:
                    entry_elements = entry_list.find_all('li', {'data-id': True})
            
            if not entry_elements:
                entry_elements = soup.find_all('div', {'class': 'content-item'})
            
            # Entry'yi bul ve o entry'den itibaren al
            start_index = None
            found_entry_on_page = False
            if entry_elements:
                for i, elem in enumerate(entry_elements):
                    parsed_entry = self._parse_entry(elem)
                    if parsed_entry and parsed_entry.get('entry_id') == entry_id:
                        start_index = i
                        found_entry_on_page = True
                        print(f"Entry bulundu, bu sayfadan itibaren alınıyor", file=sys.stderr)
                        break
                
                # Entry'den itibaren bu sayfadaki entry'leri ekle
                if start_index is not None:
                    for elem in entry_elements[start_index:]:
                        entry = self._parse_entry(elem)
                        if entry:
                            entry_id = entry.get('entry_id')
                            # Entry ID'yi işaretle (duplikasyon önleme)
                            if entry_id:
                                self.scraped_entry_ids.add(entry_id)
                            entry['title'] = title
                            entries.append(entry)
                            # Max entries kontrolü
                            if self.max_entries and len(entries) >= self.max_entries:
                                entries = entries[:self.max_entries]
                                print(f"Maksimum entry sayısına ulaşıldı ({self.max_entries}), tarama durduruluyor", file=sys.stderr)
                                break
                    # Entry'leri dosyaya yaz (incremental update)
                    if entries:
                        self._write_entries_to_file(entries)
                    # Max entries kontrolü - limit aşıldıysa dur
                    if self.max_entries and len(entries) >= self.max_entries:
                        found_start_entry = True  # Pagination loop'unu atlamak için
                else:
                    # Entry bu sayfada bulunamadı, tüm sayfayı al (focusto sayfası olduğu için entry olmalı)
                    print(f"Uyarı: Entry bu sayfada bulunamadı, tüm sayfa alınıyor", file=sys.stderr)
                    for elem in entry_elements:
                        entry = self._parse_entry(elem)
                        if entry:
                            entry_id = entry.get('entry_id')
                            # Entry ID'yi işaretle (duplikasyon önleme)
                            if entry_id:
                                self.scraped_entry_ids.add(entry_id)
                            entry['title'] = title
                            entries.append(entry)
                            # Max entries kontrolü
                            if self.max_entries and len(entries) >= self.max_entries:
                                entries = entries[:self.max_entries]
                                print(f"Maksimum entry sayısına ulaşıldı ({self.max_entries}), tarama durduruluyor", file=sys.stderr)
                                break
                    # Entry'leri dosyaya yaz (incremental update)
                    if entries:
                        self._write_entries_to_file(entries)
                    # Max entries kontrolü - limit aşıldıysa dur
                    if self.max_entries and len(entries) >= self.max_entries:
                        found_start_entry = True  # Pagination loop'unu atlamak için
                    # Entry bulunamasa bile sayfa numarası var, devam edebiliriz
                    found_entry_on_page = True
            
            page = current_page
            pagination_format = f"/{title}--{title_id}?p={{page}}"
            # Entry bulundu, entry'ler toplandı veya sayfa numarası bulundu (devam edebiliriz)
            found_start_entry = found_entry_on_page or len(entries) > 0 or current_page > 0
            if not found_entry_on_page and len(entries) == 0:
                print(f"Uyarı: Entry sayfasında entry bulunamadı, ancak sayfa {current_page}'den devam edilecek", file=sys.stderr)
            
        else:
            # Eski format: /{title}--{id}
            path_parts = path.split('--')
            if len(path_parts) < 2:
                print(f"Hata: Geçersiz entry URL formatı: {entry_url}", file=sys.stderr)
                return entries
            
            title = path_parts[0]
            entry_id = path_parts[1]
            
            print(f"Entry taranıyor: {title} (entry #{entry_id})", file=sys.stderr)
            
            # Önce belirtilen entry'yi bul
            page = 1
            found_start_entry = False
            pagination_format = None
            title_id = None
            
            # Topic ID'yi URL'den çıkarmayı dene
            if '?' in entry_url:
                query_params = parse_qs(parsed_url.query)
                if 'id' in query_params:
                    title_id = query_params['id'][0]
            
            # İlk sayfadan topic ID'yi al
            first_url = f"{self.BASE_URL}/{title}"
            first_response = self._make_request(first_url)
            if first_response:
                first_soup = BeautifulSoup(first_response.content, 'html.parser')
                response_url = first_response.url
                title_id_match = re.search(rf'/{re.escape(title)}--(\d+)', response_url)
                if title_id_match:
                    title_id = title_id_match.group(1)
                    pagination_format = f"/{title}--{title_id}?p={{page}}"
            
            # Entry'yi bulmak için sayfaları tara
            while not found_start_entry:
                if page == 1:
                    url = f"{self.BASE_URL}/{title}"
                else:
                    if pagination_format:
                        url = f"{self.BASE_URL}{pagination_format.format(page=page)}"
                    else:
                        url = f"{self.BASE_URL}/{title}?p={page}"
                
                response = self._make_request(url)
                if not response:
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # İlk sayfada topic ID ve pagination formatını çıkar
                if page == 1 and not title_id:
                    response_url = response.url
                    title_id_match = re.search(rf'/{re.escape(title)}--(\d+)', response_url)
                    if title_id_match:
                        title_id = title_id_match.group(1)
                        pagination_format = f"/{title}--{title_id}?p={{page}}"
                
                # Entry'leri bul - çoklu selector stratejisi
                entry_elements = soup.find_all('li', {'data-id': True})
                
                if not entry_elements:
                    entry_elements = soup.select('ul#entry-item-list > li')
                
                if not entry_elements:
                    entry_elements = soup.select('ul#entry-list > li')
                
                if not entry_elements:
                    entry_list = (soup.find('ul', id='entry-item-list') or 
                                soup.find('ul', id='entry-list') or 
                                soup.find('ul', class_=re.compile('entry.*list')))
                    if entry_list:
                        entry_elements = entry_list.find_all('li', {'data-id': True})
                
                if not entry_elements:
                    entry_elements = soup.find_all('li', class_=re.compile('entry'))
                
                if not entry_elements:
                    entry_elements = soup.find_all('div', {'class': 'content-item'})
                
                if not entry_elements:
                    break
                
                # Entry'yi bul
                start_index = None
                for i, elem in enumerate(entry_elements):
                    entry = self._parse_entry(elem)
                    if entry and entry.get('entry_id') == entry_id:
                        found_start_entry = True
                        entry_id_parsed = entry.get('entry_id')
                        # Entry ID'yi işaretle (duplikasyon önleme)
                        if entry_id_parsed:
                            self.scraped_entry_ids.add(entry_id_parsed)
                        entry['title'] = title
                        entries.append(entry)
                        start_index = i
                        print(f"Başlangıç entry bulundu (sayfa {page})", file=sys.stderr)
                        break
                
                if found_start_entry:
                    # Bu sayfadaki kalan entry'leri de ekle
                    if start_index is not None:
                        for elem in entry_elements[start_index + 1:]:
                            entry = self._parse_entry(elem)
                            if entry:
                                entry_id_parsed = entry.get('entry_id')
                                # Entry ID'yi işaretle (duplikasyon önleme)
                                if entry_id_parsed:
                                    self.scraped_entry_ids.add(entry_id_parsed)
                                entry['title'] = title
                                entries.append(entry)
                                # Max entries kontrolü
                                if self.max_entries and len(entries) >= self.max_entries:
                                    entries = entries[:self.max_entries]
                                    print(f"Maksimum entry sayısına ulaşıldı ({self.max_entries}), tarama durduruluyor", file=sys.stderr)
                                    break
                    # Entry'leri dosyaya yaz (incremental update)
                    if entries:
                        self._write_entries_to_file(entries)
                    # Max entries kontrolü - limit aşıldıysa dur
                    if self.max_entries and len(entries) >= self.max_entries:
                        break
                    break
                
                page += 1
                time.sleep(self.delay)
        
        # Entry bulundu veya sayfa numarası belirlendi, o sayfadan itibaren devam et
        if found_start_entry:
            # Max entries kontrolü - limit zaten aşıldıysa pagination'a girme
            if self.max_entries and len(entries) >= self.max_entries:
                print(f"Maksimum entry sayısına zaten ulaşıldı ({self.max_entries}), sayfa geçişi atlanıyor", file=sys.stderr)
            else:
                # Yeni format için: sayfa numarası zaten bulundu, o sayfadaki entry'ler alındı
                # Eski format için: entry bulundu, o sayfadaki kalan entry'ler alındı
                # Şimdi sonraki sayfalardan devam et
                page += 1
                print(f"Entry bulundu, sayfa {page}'den devam ediliyor", file=sys.stderr)
                
                while True:
                    if pagination_format:
                        url = f"{self.BASE_URL}{pagination_format.format(page=page)}"
                    elif title_id:
                        url = f"{self.BASE_URL}/{title}--{title_id}?p={page}"
                    else:
                        url = f"{self.BASE_URL}/{title}?p={page}"
                    
                    response = self._make_request(url)
                    if not response:
                        break
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # Entry'leri bul - ul#entry-item-list öncelikli
                    entry_elements = soup.find_all('li', {'data-id': True})
                    
                    if not entry_elements:
                        entry_elements = soup.select('ul#entry-item-list > li')
                    
                    if not entry_elements:
                        entry_elements = soup.select('ul#entry-list > li')
                    
                    if not entry_elements:
                        entry_list = (soup.find('ul', id='entry-item-list') or 
                                    soup.find('ul', id='entry-list'))
                        if entry_list:
                            entry_elements = entry_list.find_all('li', {'data-id': True})
                    
                    if not entry_elements:
                        entry_elements = soup.find_all('div', {'class': 'content-item'})
                    
                    if not entry_elements:
                        break
                    
                    page_entries = []
                    for elem in entry_elements:
                        entry = self._parse_entry(elem)
                        if entry:
                            entry_id_parsed = entry.get('entry_id')
                            # Entry ID'yi işaretle (duplikasyon önleme)
                            if entry_id_parsed:
                                self.scraped_entry_ids.add(entry_id_parsed)
                            entry['title'] = title
                            page_entries.append(entry)
                    
                    if not page_entries:
                        break
                    
                    entries.extend(page_entries)
                    print(f"Sayfa {page} tamamlandı, {len(page_entries)} entry bulundu (şu ana kadar toplam: {len(entries)})", file=sys.stderr)
                    
                    # Max entries kontrolü
                    if self.max_entries and len(entries) >= self.max_entries:
                        # Limit aşıldı, fazla entry'leri kaldır
                        entries = entries[:self.max_entries]
                        print(f"Maksimum entry sayısına ulaşıldı ({self.max_entries}), tarama durduruluyor", file=sys.stderr)
                        # Entry'leri dosyaya yaz (incremental update)
                        self._write_entries_to_file(entries)
                        break
                    
                    # Entry'leri dosyaya yaz (incremental update)
                    self._write_entries_to_file(entries)
                    
                    # Son sayfa kontrolü
                    last_page = self._find_last_page_from_pagination(soup)
                    if last_page and page >= last_page:
                        print(f"Son sayfa numarasına ulaşıldı ({last_page}), tarama sonlandırılıyor", file=sys.stderr)
                        break
                    
                    page += 1
                    time.sleep(self.delay)
        
        # Referans edilen entry'leri fetch et ve ilgili entry'lere ekle
        if self.fetch_referenced:
            print(f"Referans edilen entry'ler kontrol ediliyor, biraz bekleyin...", file=sys.stderr)
            referenced_entries_map = self._fetch_referenced_entries(entries)
            if referenced_entries_map:
                total_referenced = 0
                # Her entry'yi kontrol et ve referans edilen entry'leri ekle
                for entry in entries:
                    entry_id = entry.get('entry_id')
                    if entry_id in referenced_entries_map:
                        entry['referenced_content'] = referenced_entries_map[entry_id]
                        total_referenced += len(referenced_entries_map[entry_id])
                print(f"{total_referenced} referans edilen entry eklendi", file=sys.stderr)
                # Entry'leri dosyaya yaz (güncellenmiş liste ile)
                self._write_entries_to_file(entries)
        
        # referenced_entry_ids alanını tüm entry'lerden kaldır (sadece iç kullanım içindi)
        for entry in entries:
            entry.pop('referenced_entry_ids', None)
        
        return entries


def main():
    parser = argparse.ArgumentParser(
        description='Ekşi Sözlük Scraper - AI-friendly output üreten terminal tabanlı scraper. Desteklenen çıktı formatları: JSON (varsayılan), CSV (.csv), Markdown (.md, .markdown). Format dosya uzantısından otomatik tespit edilir.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  # Başlıktaki tüm entry'leri scrape et:
  eksisozluk-scraper "python"

  # Son 1 günlük entry'leri scrape et:
  eksisozluk-scraper "python" --days 1

  # Son 1 haftalık entry'leri scrape et:
  eksisozluk-scraper "python" --weeks 1

  # Son 1 aylık entry'leri scrape et:
  eksisozluk-scraper "python" --months 1

  # Son 1 yıllık entry'leri scrape et:
  eksisozluk-scraper "python" --years 1

  # Maksimum 100 entry scrape et:
  eksisozluk-scraper "python" --max-entries 100

  # Son 7 günlük, maksimum 50 entry scrape et:
  eksisozluk-scraper "python" --days 7 --max-entries 50

  # Belirli bir entry'den itibaren scrape et:
  eksisozluk-scraper "https://eksisozluk.com/python--123456"

  # Farklı çıktı formatları:
  eksisozluk-scraper "python" --output sonuclar.json  # JSON formatı
  eksisozluk-scraper "python" --output sonuclar.csv    # CSV formatı
  eksisozluk-scraper "python" --output sonuclar.md     # Markdown formatı

  # Özel parametreler:
  eksisozluk-scraper "python" --delay 2.0 --max-retries 5
        """
    )
    
    parser.add_argument('input', help='Başlık adı veya entry URL\'si')
    parser.add_argument('--days', type=int, help='Son N günlük entry\'leri scrape et')
    parser.add_argument('--weeks', type=int, help='Son N haftalık entry\'leri scrape et')
    parser.add_argument('--months', type=int, help='Son N aylık entry\'leri scrape et')
    parser.add_argument('--years', type=int, help='Son N yıllık entry\'leri scrape et')
    parser.add_argument('--delay', type=float, default=1.5, help='Request\'ler arası bekleme süresi (saniye, varsayılan: 1.5)')
    parser.add_argument('--max-retries', type=int, default=3, help='Maksimum tekrar deneme sayısı (varsayılan: 3)')
    parser.add_argument('--retry-delay', type=float, default=5.0, help='Retry arası bekleme süresi (saniye, varsayılan: 5.0)')
    parser.add_argument('--max-entries', type=int, help='Maksimum entry sayısı (varsayılan: sınırsız)')
    parser.add_argument('--output', '-o', help='Çıktı dosyası. Format dosya uzantısından otomatik tespit edilir: .json (JSON, varsayılan), .csv (CSV), .md veya .markdown (Markdown). Varsayılan: stdout (JSON)')
    parser.add_argument('--no-bkz', action='store_true', help='Referans edilen entry\'leri fetch etme (bkz özelliğini devre dışı bırak)')
    
    # Enable tab completion if argcomplete is available
    if argcomplete:
        argcomplete.autocomplete(parser)
    
    args = parser.parse_args()
    
    # Zaman filtresi hesapla
    time_filter = None
    time_filter_string = None
    if args.days:
        time_filter = timedelta(days=args.days)
        time_filter_string = f"{args.days} days"
    elif args.weeks:
        time_filter = timedelta(weeks=args.weeks)
        time_filter_string = f"{args.weeks} weeks"
    elif args.months:
        time_filter = timedelta(days=args.months * 30)  # 1 ay = 30 gün
        time_filter_string = f"{args.months} months"
    elif args.years:
        time_filter = timedelta(days=args.years * 365)  # 1 yıl = 365 gün
        time_filter_string = f"{args.years} years"
    
    # Scraper oluştur
    scraper = EksisozlukScraper(
        delay=args.delay,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        output_file=args.output,
        max_entries=args.max_entries,
        fetch_referenced=not args.no_bkz
    )
    
    # Ctrl+C durumunda dosyayı kaydetmek veya terminale yazmak için signal handler
    def signal_handler(sig, frame):
        print("\nTarama durduruldu (Ctrl+C)...", file=sys.stderr)
        # Scraper'ın mevcut entry'lerini al
        entries_to_output = scraper.current_entries if scraper.current_entries else []
        
        if args.output:
            # Output dosyası varsa dosyaya yaz
            if entries_to_output:
                scraper._write_entries_to_file(entries_to_output)
                print(f"O ana kadar toplanan {len(entries_to_output)} entry {args.output} dosyasına kaydedildi", file=sys.stderr)
        else:
            # Output dosyası yoksa terminale yazdır (tarihe göre sırala)
            if entries_to_output:
                # Entry'leri tarihe göre sırala
                sorted_entries = scraper._sort_entries_by_date(entries_to_output)
                output_data = {
                    'scrape_info': {
                        'timestamp': (scraper.scrape_start_time or datetime.now()).isoformat(),
                        'total_entries': len(sorted_entries),
                        'input': scraper.scrape_input or args.input,
                        'time_filter': scraper.scrape_time_filter or time_filter_string
                    },
                    'entries': sorted_entries
                }
                output_json = json.dumps(output_data, ensure_ascii=False, indent=2)
                print(output_json)
                print(f"O ana kadar toplanan {len(sorted_entries)} entry terminale yazdırıldı (tarihe göre sıralanmış)", file=sys.stderr)
            else:
                print("Henüz entry toplanmadı", file=sys.stderr)
        
        sys.exit(0)
    
    # Signal handler'ı kaydet (her zaman)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Entry'leri toplamak için list
    entries = []
    
    try:
        # Input'un URL mi başlık mı olduğunu kontrol et
        if args.input.startswith('http://') or args.input.startswith('https://'):
            entries = scraper.scrape_entry_and_following(args.input)
        else:
            entries = scraper.scrape_title(args.input, time_filter, time_filter_string)
    except KeyboardInterrupt:
        # Ctrl+C yakalandı
        # Signal handler zaten çalışacak, burada sadece temizlik yapabiliriz
        # Ancak signal handler'da zaten işlem yapıldığı için buraya gelmeyecek
        # Ama yine de güvenlik için burayı da güncelleyelim
        entries_to_output = scraper.current_entries if scraper.current_entries else []
        
        if args.output:
            # Output dosyası varsa dosyaya yaz
            if entries_to_output:
                scraper._write_entries_to_file(entries_to_output)
                print(f"\nINFO: O ana kadar toplanan {len(entries_to_output)} entry {args.output} dosyasına kaydedildi", file=sys.stderr)
        else:
            # Output dosyası yoksa terminale yazdır (tarihe göre sırala)
            if entries_to_output:
                # Entry'leri tarihe göre sırala
                sorted_entries = scraper._sort_entries_by_date(entries_to_output)
                output_data = {
                    'scrape_info': {
                        'timestamp': (scraper.scrape_start_time or datetime.now()).isoformat(),
                        'total_entries': len(sorted_entries),
                        'input': scraper.scrape_input or args.input,
                        'time_filter': scraper.scrape_time_filter or time_filter_string
                    },
                    'entries': sorted_entries
                }
                output_json = json.dumps(output_data, ensure_ascii=False, indent=2)
                print("\n" + output_json)
                print(f"O ana kadar toplanan {len(sorted_entries)} entry terminale yazdırıldı (tarihe göre sıralanmış)", file=sys.stderr)
        
        sys.exit(0)
    
    # Çıktıyı hazırla (output dosyası belirtilmemişse stdout'a yaz)
    if not args.output:
        # Entry'leri tarihe göre sırala
        sorted_entries = scraper._sort_entries_by_date(entries)
        output_data = {
            'scrape_info': {
                'timestamp': datetime.now().isoformat(),
                'total_entries': len(sorted_entries),
                'input': args.input,
                'time_filter': time_filter_string
            },
            'entries': sorted_entries
        }
        
        # JSON olarak çıktı ver
        output_json = json.dumps(output_data, ensure_ascii=False, indent=2)
        print(output_json)
    else:
        # Output dosyası zaten incremental olarak yazıldı, sadece bilgi ver
        print(f"Harika! Toplam {len(entries)} entry {args.output} dosyasına kaydedildi", file=sys.stderr)


if __name__ == '__main__':
    main()

