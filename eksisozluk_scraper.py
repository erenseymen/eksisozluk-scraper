#!/usr/bin/env python3
"""
Ekşi Sözlük Scraper
Terminal tabanlı, AI-friendly output üreten scraper.
"""

__version__ = "2.0.1"

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
import subprocess
import os
import shutil
import textwrap
import unicodedata
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from urllib.parse import urlparse, parse_qs, urljoin

import cloudscraper
from bs4 import BeautifulSoup

CLI_DATE_INPUT_EXAMPLE = "YYYY.MM.DD veya YYYY.MM.DD-HH:MM"


class CompactHelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Kısa ama açıklayıcı CLI yardım çıktısı için formatter."""
    pass


def _parse_cli_datetime(value: str) -> datetime:
    """Argparse için 'YYYY.MM.DD[-HH:MM]' formatında tarih/zaman ayrıştırır."""
    if not value:
        raise argparse.ArgumentTypeError("Tarih değeri boş olamaz")

    normalized = value.strip()
    parse_attempts = (
        ("%Y.%m.%d-%H:%M", "YYYY.MM.DD-HH:MM"),
        ("%Y.%m.%d", "YYYY.MM.DD"),
    )

    for fmt, _ in parse_attempts:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue

    expected_formats = ", ".join(example for _, example in parse_attempts)
    raise argparse.ArgumentTypeError(
        f"Geçersiz tarih formatı: '{value}'. Beklenen formatlar: {expected_formats}"
    )


def _format_cli_datetime(dt: datetime) -> str:
    """Metadatada kullanılmak üzere CLI tarih/zamanını string'e çevirir."""
    if dt.hour == 0 and dt.minute == 0:
        return dt.strftime("%Y.%m.%d")
    return dt.strftime("%Y.%m.%d-%H:%M")

try:
    import trafilatura  # type: ignore[import-not-found]
except ImportError:
    trafilatura = None  # type: ignore

try:
    from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore[import-not-found]
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable  # type: ignore[import-not-found]
except ImportError:
    YouTubeTranscriptApi = None  # type: ignore
    TranscriptsDisabled = None  # type: ignore
    NoTranscriptFound = None  # type: ignore
    VideoUnavailable = None  # type: ignore

try:
    from rich.console import Console
    from rich.markdown import Markdown
except ImportError:
    Console = None  # type: ignore
    Markdown = None  # type: ignore


class EksisozlukScraper:
    """Ekşi Sözlük scraper sınıfı"""
    
    BASE_URL = "https://eksisozluk.com"
    STRUCTURAL_NEWLINE_TOKEN = "__EKSISOZ_NEWLINE__"
    FILTER_CHAR_TRANSLATION = str.maketrans({
        'ı': 'i',
        'ş': 's',
        'ğ': 'g',
        'ç': 'c',
        'ö': 'o',
        'ü': 'u',
        'â': 'a',
        'î': 'i',
        'û': 'u',
    })
    
    def __init__(
        self,
        delay: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        output_file: Optional[str] = None,
        max_entries: Optional[int] = None,
        fetch_referenced: bool = True,
        fetch_external: bool = False,
        content_filters: Optional[List[str]] = None,
        filter_external_urls: bool = False,
        reverse: bool = False,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
    ):
        """
        Args:
            delay: Her request arası bekleme süresi (saniye)
            max_retries: Maksimum tekrar deneme sayısı
            retry_delay: Hata aldığında tekrar denemeden önce bekleme süresi (saniye)
            output_file: Entry'lerin yazılacağı JSON dosyası yolu (opsiyonel)
            max_entries: Maksimum entry sayısı (opsiyonel, None ise sınırsız)
            fetch_referenced: Referans edilen entry'leri fetch et (varsayılan: True)
            fetch_external: Harici URL içeriklerini ve YouTube transkriptlerini fetch et (varsayılan: False)
            content_filters: Entry içeriklerini metin bazlı filtrelemek için anahtar kelimeler listesi
            filter_external_urls: Yalnızca Ekşi Sözlük dışı URL içeren entry'leri dahil et
            reverse: Entry'leri ters sırada (son sayfadan başlayarak) tarar
        """
        self.delay = delay
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.output_file = output_file
        self.max_entries = max_entries
        self.fetch_referenced = fetch_referenced
        self.fetch_external = fetch_external
        self.filter_external_urls = filter_external_urls
        self.reverse = reverse
        self.entry_filters = [f.strip() for f in (content_filters or []) if isinstance(f, str) and f.strip()]
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime
        self._filter_groups: List[List[str]] = []
        for filter_str in self.entry_filters:
            if not isinstance(filter_str, str):
                continue
            parts = filter_str.split('|')
            normalized_parts = []
            for part in parts:
                cleaned = part.strip()
                if len(cleaned) >= 2 and (
                    (cleaned.startswith("'") and cleaned.endswith("'")) or
                    (cleaned.startswith('"') and cleaned.endswith('"'))
                ):
                    cleaned = cleaned[1:-1].strip()
                if cleaned:
                    normalized_token = self._normalize_filter_text(cleaned)
                    if normalized_token:
                        normalized_parts.append(normalized_token)
            if normalized_parts:
                self._filter_groups.append(normalized_parts)
        self.scrape_start_time = None
        self.scrape_input = None
        self.scrape_time_filter = None
        self.current_entries = []  # Mevcut entry'leri tutmak için
        self.scraped_entry_ids = set()  # Scrape edilmiş entry ID'lerini tutmak için (duplikasyon önleme)
        self.url_content_cache: Dict[str, Dict[str, Any]] = {}
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
        self.trafilatura_cli = shutil.which('trafilatura')
    
    def _normalize_filter_text(self, text: str) -> str:
        """Filtre karşılaştırması için metni normalize eder (case-insensitive + diakritiksiz)"""
        if not isinstance(text, str):
            return ''
        casefolded = text.casefold()
        normalized = unicodedata.normalize('NFKD', casefolded)
        stripped = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
        return stripped.translate(self.FILTER_CHAR_TRANSLATION)
    
    def _normalize_entry_content(self, text: str, newline_token: Optional[str] = None) -> str:
        """Entry metnindeki gereksiz satır sonlarını ve boşlukları temizler"""
        if not text:
            return ''
        
        marker = None
        if newline_token:
            marker = "__EKSISOZ_NEWLINE_MARKER__"
            text = text.replace(newline_token, marker)
        
        normalized = text.replace('\r\n', '\n').replace('\r', '\n')
        # Satır sonlarının etrafındaki boşlukları temizle
        normalized = re.sub(r'[ \t]*\n[ \t]*', '\n', normalized)
        # Tekli satır sonlarını (paragraf olmayan) boşlukla değiştir
        normalized = re.sub(r'(?<=\S)\n(?=\S)', ' ', normalized)
        # Çoklu satır sonlarını en fazla ikiye düşür
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        # Birden fazla boşluğu tek boşluğa indir
        normalized = re.sub(r'[ \t]{2,}', ' ', normalized)
        # Satır sonlarında kalan boşlukları temizle
        normalized = re.sub(r' *\n', '\n', normalized)
        normalized = re.sub(r'\n *', '\n', normalized)
        # Parantez ve noktalama öncesindeki boşlukları temizle
        normalized = re.sub(r'\( ', '(', normalized)
        normalized = re.sub(r' \)', ')', normalized)
        normalized = re.sub(r' (?=[,:;!?])', '', normalized)
        normalized = re.sub(r' (?=[\'’])', '', normalized)
        
        if marker:
            normalized = normalized.replace(marker, newline_token)
        
        return normalized.strip()
    
    def _format_referenced_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """referenced_content listesi için alanları istenen sıraya göre düzenler"""
        if not isinstance(entry, dict):
            return entry
        
        entry_type = entry.get('type', 'entry')
        formatted: Dict[str, Any] = {'type': entry_type}
        
        ordered_keys = ['title', 'entry_id', 'author', 'date', 'content']
        for key in ordered_keys:
            if key in entry:
                formatted[key] = entry[key]
        
        for key, value in entry.items():
            if key == 'type' or key in ordered_keys:
                continue
            formatted[key] = value
        
        return formatted
    
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
                pending_external_urls = []
                seen_urls = set()
                has_external_url = False
                
                if self.fetch_referenced:
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
                
                # Entry içindeki harici URL'leri topla
                all_links = content_elem.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '').strip()
                    if not href:
                        continue
                    # Entry referanslarını atla (onlar ayrı handle edilecek)
                    if re.search(r'(?:/entry/|entry--)\d+', href):
                        continue
                    if href.startswith('#'):
                        continue
                    
                    absolute_url = urljoin(f"{self.BASE_URL}/", href)
                    if absolute_url.startswith('//'):
                        absolute_url = f"https:{absolute_url}"
                    
                    parsed_url = urlparse(absolute_url)
                    if parsed_url.netloc.endswith('eksisozluk.com'):
                        continue
                    
                    has_external_url = True
                    
                    if not self.fetch_external:
                        continue
                    
                    if absolute_url in seen_urls:
                        continue
                    
                    link_text = link.get_text(strip=True)
                    url_item = {
                        'type': 'url',
                        'url': absolute_url,
                    }
                    if link_text:
                        url_item['text'] = link_text
                    
                    pending_external_urls.append(url_item)
                    seen_urls.add(absolute_url)
                
                entry_data['has_external_url'] = has_external_url
                
                if self.fetch_external and pending_external_urls:
                    entry_data['_pending_external_urls'] = pending_external_urls
                
                # HTML tag'lerini temizle ama formatı koru
                # Gizli açıklamaları (ör: * işaretli) içeriğe dahil et
                for sup in content_elem.find_all('sup'):
                    classes = sup.get('class') or []
                    if 'ab' not in classes:
                        continue
                    
                    tooltip_text = ''
                    anchor = sup.find('a')
                    if anchor:
                        tooltip_text = (
                            anchor.get('title') or
                            anchor.get('data-title') or
                            anchor.get('aria-label') or
                            anchor.get_text(strip=True)
                        )
                    else:
                        tooltip_text = (
                            sup.get('title') or
                            sup.get('data-title') or
                            sup.get('aria-label') or
                            sup.get_text(strip=True)
                        )
                    
                    if tooltip_text:
                        tooltip_text = tooltip_text.strip()
                        if tooltip_text.startswith('('):
                            replacement_text = f" {tooltip_text}"
                        else:
                            replacement_text = f" ({tooltip_text})"
                    else:
                        replacement_text = ''
                    
                    sup.replace_with(replacement_text)
                
                for br in content_elem.find_all('br'):
                    br.replace_with(self.STRUCTURAL_NEWLINE_TOKEN)
                for p in content_elem.find_all('p'):
                    p.append(self.STRUCTURAL_NEWLINE_TOKEN)
                raw_content = content_elem.get_text(separator='\n', strip=True)
                normalized_content = self._normalize_entry_content(
                    raw_content,
                    newline_token=self.STRUCTURAL_NEWLINE_TOKEN
                )
                final_content = normalized_content.replace(self.STRUCTURAL_NEWLINE_TOKEN, '\n')
                final_content = re.sub(r'[ \t]*\n[ \t]*', '\n', final_content)
                entry_data['content'] = final_content
            
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
    
    def _entry_matches_filters(self, entry: Dict[str, Any]) -> bool:
        """Entry'nin içerik filtreleri ile eşleşip eşleşmediğini kontrol eder"""
        if self._filter_groups:
            content_parts = [
                entry.get('content', ''),
                entry.get('author', ''),
                entry.get('title', ''),
                entry.get('date', ''),
                entry.get('entry_id', ''),
            ]
            
            haystack_raw = ' '.join(part for part in content_parts if isinstance(part, str))
            haystack = self._normalize_filter_text(haystack_raw)
            for group in self._filter_groups:
                if not any(token in haystack for token in group):
                    return False
        
        if self.filter_external_urls and not entry.get('has_external_url'):
            return False
        
        return True
    
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
    
    def _extract_with_trafilatura(self, html: str, url: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """trafilatura ile HTML içeriğinden metin çıkarır"""
        if trafilatura is None:
            return self._extract_with_trafilatura_cli(url)
        
        try:
            config = trafilatura.settings.use_config()
            extracted_json = trafilatura.extract(
                html,
                url=url,
                output_format='json',
                with_metadata=True,
                include_comments=False,
                include_images=False,
                config=config,
            )
            result: Dict[str, Any] = {}
            parse_error: Optional[str] = None
            if extracted_json:
                try:
                    extracted_data = json.loads(extracted_json)
                except json.JSONDecodeError:
                    extracted_data = {}
                    parse_error = "trafilatura JSON parse edilemedi"
                
                if extracted_data:
                    main_text = (extracted_data.get('text') or '').strip()
                    if main_text:
                        result['content'] = main_text
                    
                    title = extracted_data.get('title') or extracted_data.get('sitename')
                    if title:
                        result['title'] = title.strip()
                    
                    description = extracted_data.get('description')
                    if description:
                        result['summary'] = description.strip()
                    
                    author = extracted_data.get('author')
                    if author:
                        result['author'] = author
                    
                    language = extracted_data.get('language')
                    if language:
                        result['language'] = language
                    
                    publish_date = extracted_data.get('date')
                    if publish_date:
                        result['date'] = publish_date
            
            if not result:
                bare_extracted = trafilatura.bare_extraction(
                    html,
                    url=url,
                    no_fallback=False,
                    include_comments=False,
                    include_images=False,
                    favor_precision=False,
                )
                if bare_extracted:
                    main_text = (bare_extracted.get('text') or '').strip()
                    if main_text:
                        result['content'] = main_text
                    title = bare_extracted.get('title')
                    if title:
                        result.setdefault('title', title.strip())
                    author = bare_extracted.get('author')
                    if author:
                        result.setdefault('author', author)
                    publish_date = bare_extracted.get('date')
                    if publish_date:
                        result.setdefault('date', publish_date)
            
            if result:
                return result, parse_error
            
            # Python modülü sonuç vermediyse CLI ile dene
            cli_result, cli_error = self._extract_with_trafilatura_cli(url)
            warnings = []
            if parse_error:
                warnings.append(parse_error)
            if cli_error:
                warnings.append(cli_error)
            aggregated_warning = '; '.join(warnings) if warnings else None
            return cli_result, aggregated_warning
        
        except Exception as exc:
            cli_result, cli_error = self._extract_with_trafilatura_cli(url)
            warnings = [str(exc)]
            if cli_error:
                warnings.append(cli_error)
            aggregated_warning = '; '.join(warnings) if warnings else None
            return cli_result, aggregated_warning

    def _extract_with_trafilatura_cli(self, url: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """trafilatura CLI (pipx ile kurulmuş olabilir) üzerinden içerik çıkarır"""
        if not self.trafilatura_cli:
            return None, None
        
        try:
            process = subprocess.run(
                [self.trafilatura_cli, '--json', '--with-metadata', '-u', url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60
            )
        except Exception as exc:
            return None, f"trafilatura CLI çalıştırılamadı: {exc}"
        
        stderr_output = process.stderr.strip()
        if process.returncode != 0:
            error_msg = stderr_output or f"trafilatura CLI {process.returncode} kodu ile sonlandı"
            return None, error_msg
        
        stdout = process.stdout.strip()
        if not stdout:
            return None, stderr_output or "trafilatura CLI çıktı üretmedi"
        
        try:
            extracted_data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            return None, f"trafilatura CLI çıktısı JSON parse edilemedi: {exc}"
        
        result: Dict[str, Any] = {}
        
        main_text = (extracted_data.get('text') or '').strip()
        if main_text:
            result['content'] = main_text
        
        title = extracted_data.get('title') or extracted_data.get('sitename')
        if title:
            result['title'] = title.strip()
        
        description = extracted_data.get('description')
        if description:
            result['summary'] = description.strip()
        
        author = extracted_data.get('author')
        if author:
            result['author'] = author
        
        language = extracted_data.get('language')
        if language:
            result['language'] = language
        
        publish_date = extracted_data.get('date')
        if publish_date:
            result['date'] = publish_date
        
        return (result if result else None), (stderr_output or None)
    
    def _extract_youtube_video_id(self, url: str) -> Optional[str]:
        """YouTube URL'inden video ID'sini çıkarır"""
        if not url:
            return None
        
        # YouTube URL pattern'leri
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _fetch_youtube_transcript(self, video_id: str) -> Optional[str]:
        """YouTube video transkriptini çeker"""
        if YouTubeTranscriptApi is None:
            return None
        
        try:
            # Yeni API: YouTubeTranscriptApi instance oluştur ve list() metodunu kullan
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            transcript_data = None
            
            # Öncelik sırasına göre transkript dene
            # 1. Türkçe manuel transkript
            try:
                transcript = transcript_list.find_manually_created_transcript(['tr', 'tr-TR'])
                transcript_data = transcript.fetch()
            except Exception:
                pass
            
            # 2. Türkçe otomatik transkript
            if transcript_data is None:
                try:
                    transcript = transcript_list.find_generated_transcript(['tr', 'tr-TR'])
                    transcript_data = transcript.fetch()
                except Exception:
                    pass
            
            # 3. İngilizce manuel transkript
            if transcript_data is None:
                try:
                    transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
                    transcript_data = transcript.fetch()
                except Exception:
                    pass
            
            # 4. İngilizce otomatik transkript
            if transcript_data is None:
                try:
                    transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
                    transcript_data = transcript.fetch()
                except Exception:
                    pass
            
            # 5. Herhangi bir manuel transkript
            if transcript_data is None:
                try:
                    for transcript in transcript_list:
                        if not transcript.is_generated:
                            transcript_data = transcript.fetch()
                            break
                except Exception:
                    pass
            
            # 6. Herhangi bir transkript (manuel veya otomatik)
            if transcript_data is None:
                try:
                    for transcript in transcript_list:
                        transcript_data = transcript.fetch()
                        break
                except Exception:
                    pass
            
            # Transkript verilerini metin olarak birleştir
            # Yeni API: item['text'] yerine item.text kullan (FetchedTranscriptSnippet objesi)
            if transcript_data:
                transcript_text = ' '.join([item.text for item in transcript_data])
                return transcript_text.strip()
            
            return None
            
        except Exception as e:
            # VideoUnavailable veya diğer hatalar için None döndür
            if VideoUnavailable is not None and isinstance(e, VideoUnavailable):
                return None
            # Diğer hatalar için de None döndür
            return None
    
    def _fetch_url_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Entry içerisinde paylaşılan URL'lerin içeriğini getirir"""
        if not url:
            return None
        
        if not self.fetch_external:
            return None
        
        if url in self.url_content_cache:
            return self.url_content_cache[url]
        
        result: Dict[str, Any] = {'type': 'url'}
        extraction_warning: Optional[str] = None
        
        # YouTube URL'i kontrolü - önce transkript çekmeyi dene
        video_id = self._extract_youtube_video_id(url)
        if video_id:
            transcript = self._fetch_youtube_transcript(video_id)
            result['type'] = 'youtube'
            result['url'] = url
            result['video_id'] = video_id
            
            if transcript:
                result['content'] = transcript
            else:
                result['content'] = '(Transkript mevcut değil veya alınamadı)'
            
            # Video başlığını almak için YouTube sayfasını çekmeyi dene
            try:
                response = self.session.get(url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # Önce title tag'ini dene
                    title_elem = soup.find('title')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        # " - YouTube" kısmını kaldır
                        if title.endswith(' - YouTube'):
                            title = title[:-10].strip()
                        if title and title != 'YouTube':
                            result['title'] = title
                    # Title bulunamazsa meta og:title'ı dene
                    if 'title' not in result:
                        meta_title = soup.find('meta', property='og:title')
                        if meta_title and meta_title.get('content'):
                            result['title'] = meta_title.get('content').strip()
            except Exception:
                pass  # Başlık alınamazsa devam et
            
            self.url_content_cache[url] = result
            if self.delay:
                time.sleep(self.delay)
            return result
        
        # Önce trafilatura ile içerik çıkarmayı dene
        if trafilatura is not None:
            try:
                downloaded_html = trafilatura.fetch_url(url)
                if downloaded_html:
                    extracted_data, extraction_warning = self._extract_with_trafilatura(downloaded_html, url)
                    if extracted_data and extracted_data.get('content'):
                        result.update(extracted_data)
                        self.url_content_cache[url] = result
                        if self.delay:
                            time.sleep(self.delay)
                        return result
            except Exception as exc:
                extraction_warning = str(exc)
        elif self.trafilatura_cli:
            extracted_data, extraction_warning = self._extract_with_trafilatura_cli(url)
            if extracted_data and extracted_data.get('content'):
                result.update(extracted_data)
                self.url_content_cache[url] = result
                if self.delay:
                    time.sleep(self.delay)
                return result
        
        try:
            response = self.session.get(url, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'text/html' in content_type:
                helper_warning: Optional[str] = None
                extracted_data: Optional[Dict[str, Any]] = None
                
                if trafilatura is not None:
                    extracted_data, helper_warning = self._extract_with_trafilatura(response.text, url)
                elif self.trafilatura_cli:
                    extracted_data, helper_warning = self._extract_with_trafilatura_cli(url)
                    if helper_warning and not extraction_warning:
                        extraction_warning = helper_warning
                    if extracted_data and extracted_data.get('content'):
                        result.update(extracted_data)
                
                if 'content' not in result:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    for tag in soup(['script', 'style', 'noscript']):
                        tag.decompose()
                    
                    title_elem = soup.find('title')
                    if title_elem:
                        result.setdefault('title', title_elem.get_text(strip=True))
                    
                    body_text = soup.get_text(separator='\n', strip=True)
                    body_text = re.sub(r'\n{3,}', '\n\n', body_text)
                    if len(body_text) > 2000:
                        body_text = body_text[:2000].rstrip() + '...'
                    result['content'] = body_text
            
            elif 'application/json' in content_type:
                try:
                    json_data = response.json()
                    json_text = json.dumps(json_data, ensure_ascii=False, indent=2)
                except Exception:
                    json_text = response.text
                if len(json_text) > 2000:
                    json_text = json_text[:2000].rstrip() + '...'
                result['content'] = json_text
            
            elif 'text/plain' in content_type or 'text/' in content_type:
                text_content = response.text.strip()
                if len(text_content) > 2000:
                    text_content = text_content[:2000].rstrip() + '...'
                result['content'] = text_content
            
            else:
                truncated_type = content_type.split(';')[0] if content_type else 'bilinmiyor'
                result['content'] = f"(Desteklenmeyen içerik türü: {truncated_type})"
            
            if extraction_warning:
                result['extraction_warning'] = extraction_warning[:200]
            
            self.url_content_cache[url] = result
            if self.delay:
                time.sleep(self.delay)
            return result
        
        except Exception as e:
            error_message = str(e)
            if extraction_warning:
                error_message = f"{extraction_warning}; fallback_error={error_message}"
            error_result = {
                'type': 'url',
                'error': error_message[:500]
            }
            self.url_content_cache[url] = error_result
            return error_result
    
    def _populate_entry_referenced_content(self, entry: Dict[str, Any]) -> None:
        """Entry için ertelenmiş URL içeriklerini fetch eder ve referenced_content'e ekler"""
        pending_urls = entry.pop('_pending_external_urls', None)
        
        if not pending_urls:
            return
        
        if not self.fetch_external:
            return
        
        referenced_content = entry.setdefault('referenced_content', [])
        
        for pending in pending_urls:
            if not isinstance(pending, dict):
                continue
            
            url = pending.get('url')
            if not url:
                continue
            
            fetched = self._fetch_url_content(url)
            if fetched:
                merged = dict(fetched)
            else:
                merged = {'type': 'url'}
            
            merged.setdefault('url', url)
            
            for key, value in pending.items():
                if key in merged:
                    continue
                merged[key] = value
            
            formatted = self._format_referenced_entry(merged)
            referenced_content.append(formatted)
    
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
                    referenced_entry_copy.setdefault('type', 'entry')
                    formatted_entry = self._format_referenced_entry(referenced_entry_copy)
                    referenced_entries_map[entry_id].append(formatted_entry)
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
                    referenced_entry_copy.setdefault('type', 'entry')
                    formatted_entry = self._format_referenced_entry(referenced_entry_copy)
                    referenced_entries_map[parent_entry_id].append(formatted_entry)
                
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
    
    def _reorder_entry_fields(self, entry: Dict) -> Dict:
        """Entry dictionary'sini istenen sıraya göre yeniden düzenler: title, entry_id, author, date, content, referenced_content"""
        # İstenen sıra
        field_order = ['title', 'entry_id', 'author', 'date', 'content', 'referenced_content']
        
        # Yeni dictionary oluştur - önce sıralı alanlar, sonra diğerleri
        reordered = {}
        
        # Önce sıralı alanları ekle
        for field in field_order:
            if field in entry:
                reordered[field] = entry[field]
        
        # Sonra diğer tüm alanları ekle (zaten eklenmiş olanları atla)
        for key, value in entry.items():
            if key not in reordered:
                reordered[key] = value
        
        return reordered
    
    def _reorder_entries(self, entries: List[Dict]) -> List[Dict]:
        """Entry listesindeki tüm entry'leri yeniden sıralar"""
        return [self._reorder_entry_fields(entry) for entry in entries]
    
    def _write_json(self, entries: List[Dict]):
        """Entry'leri JSON formatında yazar"""
        # Entry'leri yeniden sırala
        reordered_entries = self._reorder_entries(entries)
        
        output_data = {
            'scrape_info': {
                'timestamp': (self.scrape_start_time or datetime.now()).isoformat(),
                'total_entries': len(reordered_entries),
                'input': self.scrape_input or '',
                'time_filter': self.scrape_time_filter,
            'filters': self.entry_filters,
            'filter_external_urls': self.filter_external_urls
            },
            'entries': reordered_entries
        }
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    def _write_csv(self, entries: List[Dict]):
        """Entry'leri CSV formatında yazar"""
        # Entry'leri yeniden sırala
        reordered_entries = self._reorder_entries(entries)
        
        with open(self.output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            # Scrape info'yu yorum olarak yaz
            scrape_info = {
                'timestamp': (self.scrape_start_time or datetime.now()).isoformat(),
                'total_entries': len(reordered_entries),
                'input': self.scrape_input or '',
                'time_filter': self.scrape_time_filter,
                'filters': self.entry_filters
            }
            f.write(f"# Scrape Info: {json.dumps(scrape_info, ensure_ascii=False)}\n")
            
            # CSV başlıkları - istenen sıraya göre
            headers = ['title', 'entry_id', 'author', 'date', 'content', 'referenced_content']
            writer.writerow(headers)
            
            # Entry'leri yaz
            for entry in reordered_entries:
                # referenced_content'i JSON string olarak serialize et
                referenced_content = entry.get('referenced_content', [])
                referenced_content_str = json.dumps(referenced_content, ensure_ascii=False) if referenced_content else ''
                
                row = [
                    entry.get('title', ''),
                    entry.get('entry_id', ''),
                    entry.get('author', ''),
                    entry.get('date', ''),
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
                'time_filter': self.scrape_time_filter,
                'filters': self.entry_filters
            }
            f.write(f"- **Timestamp**: {scrape_info['timestamp']}\n")
            f.write(f"- **Total Entries**: {scrape_info['total_entries']}\n")
            f.write(f"- **Input**: {scrape_info['input']}\n")
            if scrape_info['time_filter']:
                f.write(f"- **Time Filter**: {scrape_info['time_filter']}\n")
            if scrape_info['filters']:
                formatted_filters = ', '.join(scrape_info['filters'])
                f.write(f"- **Filters**: {formatted_filters}\n")
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
                        ref_type = ref_entry.get('type', 'entry')
                        
                        if ref_type == 'url':
                            ref_url = ref_entry.get('url', '')
                            ref_text = ref_entry.get('text', '')
                            ref_title = ref_entry.get('title', '')
                            ref_content = ref_entry.get('content', '')
                            ref_error = ref_entry.get('error', '')
                            
                            f.write(f"#### Referenced URL {ref_idx}\n\n")
                            if ref_text:
                                f.write(f"- **Text**: {ref_text}\n")
                            if ref_url:
                                f.write(f"- **URL**: {ref_url}\n")
                            if ref_title:
                                f.write(f"- **Title**: {ref_title}\n")
                            if ref_content:
                                f.write("- **Content**:\n\n")
                                f.write(f"{ref_content}\n")
                            if ref_error:
                                f.write(f"- **Error**: {ref_error}\n")
                            f.write("\n")
                            continue
                        
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
        absolute_filter_active = bool(self.start_datetime or self.end_datetime)
        # Zaman filtresi string'ini Türkçeleştir
        if absolute_filter_active:
            if self.start_datetime and self.end_datetime:
                start_label = _format_cli_datetime(self.start_datetime)
                end_label = _format_cli_datetime(self.end_datetime)
                self.scrape_time_filter = f"{start_label} ile {end_label} arası"
            elif self.start_datetime:
                start_label = _format_cli_datetime(self.start_datetime)
                self.scrape_time_filter = f"{start_label} ve sonrası"
            elif self.end_datetime:
                end_label = _format_cli_datetime(self.end_datetime)
                self.scrape_time_filter = f"{end_label} ve öncesi"
        elif time_filter_string:
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
        
        # Kullanıcı ters sıralama isterse veya relativ zaman filtresi aktifse son sayfadan başlayabiliriz
        reverse_order = self.reverse and not absolute_filter_active
        last_page = None  # Son sayfa numarası
        
        if self.reverse:
            print("Ters sıralı tarama modu aktif: Entry'ler son sayfadan başlayarak indirilecek", file=sys.stderr)
        
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
                    
                    # Zaman filtresi veya ters sıralama isteği varsa son sayfadan başla
                    if time_filter or reverse_order:
                        page = last_page
                        reverse_order = True
                        reasons = []
                        if time_filter:
                            reasons.append("zaman filtresi aktif")
                        if self.reverse and not absolute_filter_active:
                            reasons.append("ters sıralı tarama seçildi")
                        reason_text = f" ({', '.join(reasons)})" if reasons else ""
                        print(f"Son sayfadan başlayıp geriye doğru taranıyor{reason_text} (başlangıç sayfası {last_page})", file=sys.stderr)
                        # İlk sayfayı atla, direkt son sayfaya git
                        continue
                else:
                    print(f"Uyarı: Son sayfa bulunamadı", file=sys.stderr)
                    if self.reverse:
                        print("Bilgi: Ters sıralı tarama devre dışı bırakıldı (son sayfa bulunamadı)", file=sys.stderr)
                        reverse_order = False
            
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
            all_entries_too_old = bool(time_filter)
            all_entries_before_start = bool(self.start_datetime)
            
            for elem in entry_elements:
                entry = self._parse_entry(elem)
                if entry:
                    entry_id = entry.get('entry_id')
                    # Entry ID'yi işaretle (duplikasyon önleme)
                    if entry_id:
                        self.scraped_entry_ids.add(entry_id)
                    
                    entry_dt: Optional[datetime] = None
                    needs_datetime = time_filter or absolute_filter_active
                    if needs_datetime:
                        entry_dt = self._parse_datetime(entry.get('date', ''))
                        if not entry_dt:
                            # Tarih parse edilemezse mutlak/zaman filtresi aktifken entry'yi dahil etme
                            continue

                    within_relative_range = True
                    if time_filter and entry_dt:
                        entry_age = datetime.now() - entry_dt
                        within_relative_range = entry_age <= time_filter
                        if within_relative_range:
                            all_entries_too_old = False

                    within_absolute_range = True
                    if absolute_filter_active and entry_dt:
                        before_start = bool(self.start_datetime and entry_dt < self.start_datetime)
                        after_end = bool(self.end_datetime and entry_dt > self.end_datetime)
                        if self.start_datetime and not before_start:
                            all_entries_before_start = False
                        within_absolute_range = not before_start and not after_end

                    include_entry = within_relative_range and within_absolute_range

                    if include_entry:
                        entry['title'] = title
                        if self._entry_matches_filters(entry):
                            self._populate_entry_referenced_content(entry)
                            page_entries.append(entry)
                        else:
                            # Filtrelere takılsa bile zaman aralığında bir entry bulunduğunu not et
                            if not time_filter:
                                all_entries_too_old = False
                        if not time_filter:
                            all_entries_too_old = False
                    else:
                        if time_filter and not within_relative_range:
                            # Entry zaman filtresi dışında kaldı
                            pass
                        if absolute_filter_active and self.start_datetime and entry_dt and entry_dt >= self.start_datetime:
                            all_entries_before_start = False
            
            if reverse_order and page_entries:
                page_entries.sort(
                    key=lambda e: self._parse_datetime(e.get('date', '')) or datetime.min,
                    reverse=True,
                )
            
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

            if (
                absolute_filter_active
                and self.start_datetime
                and all_entries_before_start
                and reverse_order
            ):
                print("Belirlenen başlangıç tarihinden daha eski entry'lere ulaşıldı, tarama durduruluyor", file=sys.stderr)
                break
            
            # Sayfa navigasyonu
            if reverse_order:
                # Ters sırada: önceki sayfaya git
                page -= 1
                if page < 1:
                    break
            else:
                # Normal sırada: sonraki sayfaya git
                # Eğer bu sayfada entry yoksa dur (zaman filtresi yoksa)
                if (
                    not page_entries
                    and not time_filter
                    and not absolute_filter_active
                    and not self.entry_filters
                    and not self.filter_external_urls
                ):
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
            total_referenced = 0
            # Her entry'yi kontrol et ve referans edilen entry'leri ekle
            for entry in entries:
                entry_id = entry.get('entry_id')
                if not entry_id:
                    continue
                
                existing_referenced_content = entry.setdefault('referenced_content', [])
                
                if referenced_entries_map and entry_id in referenced_entries_map:
                    fetched_references = referenced_entries_map[entry_id]
                    if fetched_references:
                        existing_referenced_content.extend(fetched_references)
                        total_referenced += len(fetched_references)
            
            if total_referenced > 0:
                print(f"{total_referenced} referans edilen entry eklendi", file=sys.stderr)
                # Entry'leri dosyaya yaz (güncellenmiş liste ile)
                self._write_entries_to_file(entries)
        
        # referenced_entry_ids alanını tüm entry'lerden kaldır (sadece iç kullanım içindi)
        for entry in entries:
            entry.pop('referenced_entry_ids', None)
        
        # Eğer son sayfadan başlanarak alındıysa ve output dosyası belirtilmişse, gerekirse tekrar yaz
        if reverse_order and self.output_file:
            if self.reverse:
                print("Ters sıralı tarama tamamlandı, sonuçlar son entry'den başlayarak kaydedildi", file=sys.stderr)
                self._write_entries_to_file(entries)
            else:
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
                    if self.reverse:
                        indices = range(start_index, -1, -1)
                    else:
                        indices = range(start_index, len(entry_elements))
                    for idx in indices:
                        elem = entry_elements[idx]
                        entry = self._parse_entry(elem)
                        if entry:
                            parsed_entry_id = entry.get('entry_id')
                            # Entry ID'yi işaretle (duplikasyon önleme)
                            if parsed_entry_id:
                                self.scraped_entry_ids.add(parsed_entry_id)
                            entry['title'] = title
                            if self._entry_matches_filters(entry):
                                self._populate_entry_referenced_content(entry)
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
                    iterable = entry_elements if not self.reverse else reversed(entry_elements)
                    for elem in iterable:
                        entry = self._parse_entry(elem)
                        if entry:
                            parsed_entry_id = entry.get('entry_id')
                            # Entry ID'yi işaretle (duplikasyon önleme)
                            if parsed_entry_id:
                                self.scraped_entry_ids.add(parsed_entry_id)
                            entry['title'] = title
                            if self._entry_matches_filters(entry):
                                self._populate_entry_referenced_content(entry)
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
                        if self._entry_matches_filters(entry):
                            self._populate_entry_referenced_content(entry)
                            entries.append(entry)
                        start_index = i
                        print(f"Başlangıç entry bulundu (sayfa {page})", file=sys.stderr)
                        break
                
                if found_start_entry:
                    # Bu sayfadaki kalan entry'leri de ekle
                    if start_index is not None:
                        if self.reverse:
                            indices = range(start_index - 1, -1, -1)
                        else:
                            indices = range(start_index + 1, len(entry_elements))
                        for idx in indices:
                            elem = entry_elements[idx]
                            entry = self._parse_entry(elem)
                            if entry:
                                entry_id_parsed = entry.get('entry_id')
                                # Entry ID'yi işaretle (duplikasyon önleme)
                                if entry_id_parsed:
                                    self.scraped_entry_ids.add(entry_id_parsed)
                                entry['title'] = title
                                if self._entry_matches_filters(entry):
                                    self._populate_entry_referenced_content(entry)
                                    entries.append(entry)
                                # Max entries kontrolü
                                if self.max_entries and len(entries) >= self.max_entries:
                                    entries = entries[:self.max_entries]
                                    print(f"Maksimum entry sayısına ulaşıldı ({self.max_entries}), tarama durduruluyor", file=sys.stderr)
                                    break
                        # Reverse modunda ilk sayfada daha eski entry yoksa bir sonraki (önceki) sayfaya geçilecek
                    else:
                        iterable = entry_elements if not self.reverse else reversed(entry_elements)
                        for elem in iterable:
                            entry = self._parse_entry(elem)
                            if entry:
                                entry_id_parsed = entry.get('entry_id')
                                # Entry ID'yi işaretle (duplikasyon önleme)
                                if entry_id_parsed:
                                    self.scraped_entry_ids.add(entry_id_parsed)
                                entry['title'] = title
                                if self._entry_matches_filters(entry):
                                    self._populate_entry_referenced_content(entry)
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
                if self.reverse:
                    # Entry'den önceki sayfalara git
                    page -= 1
                    if page >= 1:
                        print(f"Entry bulundu, önceki sayfalar taranıyor (başlangıç sayfası {page})", file=sys.stderr)
                    while page >= 1:
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
                        for elem in reversed(entry_elements):
                            entry = self._parse_entry(elem)
                            if entry:
                                entry_id_parsed = entry.get('entry_id')
                                # Entry ID'yi işaretle (duplikasyon önleme)
                                if entry_id_parsed:
                                    self.scraped_entry_ids.add(entry_id_parsed)
                                entry['title'] = title
                                if self._entry_matches_filters(entry):
                                    self._populate_entry_referenced_content(entry)
                                    page_entries.append(entry)
                        
                        if not page_entries and not self.entry_filters:
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
                        
                        page -= 1
                        time.sleep(self.delay)
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
                                if self._entry_matches_filters(entry):
                                    self._populate_entry_referenced_content(entry)
                                    page_entries.append(entry)
                        
                        if not page_entries and not self.entry_filters:
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


# Gemini prompt'ları
GEMINI_SUMMARY_PROMPT = """Aşağıda JSON formatında verilen Ekşi Sözlük entry'lerini analiz ederek kapsamlı bir özet hazırla.

## Görev:
- Ana konuları ve tartışma başlıklarını belirle
- Farklı görüşler ve fikir ayrılıklarını dengeli bir şekilde sun
- Mizahi, ironik veya dikkat çekici entry'leri vurgula
- Özgün ve derinlemesine görüşleri öne çıkar
- Entry'lerin kronolojik veya tematik akışını göz önünde bulundur

## Format ve Dil:
- Markdown formatında yaz (başlıklar, listeler, vurgular kullan)
- Bilgi verici, tarafsız ve profesyonel bir dil kullan
- Akıcı ve okunabilir bir metin oluştur
- Gereksiz spekülasyon veya çıkarımdan kaçın
- Entry'lerden kısa ve anlamlı alıntılar ekle (tırnak işareti ile)

## Link Formatı:
- Entry'lere referans verirken Markdown link formatı kullan: [link metni](https://eksisozluk.com/entry/{entry_id})
- JSON'daki entry_id değerini kullanarak link oluştur
- Link metni entry'nin anahtar kelimesini veya bağlama uygun bir ifadeyi içersin

## Çıktı:
Yanıtın sadece özet metni olsun, ek açıklama veya meta bilgi içermesin."""

GEMINI_BLOG_PROMPT = """Aşağıda JSON formatında verilen Ekşi Sözlük entry'lerine dayalı, kapsamlı ve okunabilir bir blog yazısı yaz.

## Görev
Entry'lerdeki farklı görüşleri, deneyimleri, mizahı ve eleştirileri sentezleyerek, konuyu derinlemesine ele alan bir blog yazısı oluştur.

## Yazı Üslubu ve Stil
- Akıcı, samimi ve erişilebilir bir dil kullan
- Analitik ve düşündürücü ol, ancak akademik bir üsluptan kaçın
- Farklı perspektifleri dengeli bir şekilde sun
- Gerektiğinde örnekler, anekdotlar ve ilginç detaylar ekle
- Spekülasyondan kaçın, yalnızca entry'lerdeki bilgileri kullan

## İçerik Yapısı
1. Giriş: Konuyu kısa bir özetle tanıt ve entry'lerden çıkan ana temaları belirt
2. Gelişme: Farklı bakış açılarını, görüşleri ve deneyimleri kategorize ederek sun
3. Sonuç: Genel gözlemler ve öne çıkan noktaları özetle

## Alıntı Formatı
Her alıntı şu formatta olsun:
> [Entry içeriği]
> 
> — **{yazar}** · [{tarih}](https://eksisozluk.com/entry/{entry_id})

Notlar:
- Yukarıdaki satırı aynen bu Markdown yapısıyla üret (tarih tıklanabilir link olsun).

## Çıktı Formatı
- Yanıt YALNIZCA blog yazısı olsun (Markdown formatında)
- Başlık, alt başlıklar ve paragrafları uygun şekilde formatla
- Entry'lerden bol bol alıntı yap, farklı görüşleri yansıt
- Her alıntıda yazar, tarih ve link bilgilerini mutlaka ekle"""


def _get_gemini_cli_path() -> Optional[str]:
    """Gemini CLI'nin mevcut yolu döner (yoksa None)"""
    return shutil.which('gemini')


def _generate_gemini_output(json_data: str, prompt: str, use_flash: bool = False) -> Optional[str]:
    """Gemini CLI'yi kullanarak JSON verisinden çıktı üretir
    
    Args:
        json_data: JSON formatında entry verisi
        prompt: Gemini'ye gönderilecek prompt
        use_flash: Flash modelini kullan (daha hızlı, daha düşük kalite)
    """
    gemini_path = _get_gemini_cli_path()
    if not gemini_path:
        print("Hata: Gemini CLI bulunamadı. Lütfen 'gemini' komutunu kurun.", file=sys.stderr)
        return None
    
    try:
        # Gemini CLI'yi çağır
        extra_args: List[str] = []
        if use_flash:
            extra_args.extend(['-m', 'gemini-2.5-flash'])
        extra_args.extend(['-p', prompt])

        if os.name == 'nt' and gemini_path.lower().endswith(('.cmd', '.bat')):
            cmd = ['cmd.exe', '/c', gemini_path, *extra_args]
        else:
            cmd = [gemini_path, *extra_args]
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        stdout, stderr = process.communicate(input=json_data, timeout=300)  # 5 dakika timeout
        
        if process.returncode != 0:
            print(f"Gemini CLI hatası: {stderr}", file=sys.stderr)
            return None
        
        return stdout.strip()
    
    except subprocess.TimeoutExpired:
        print("Hata: Gemini CLI yanıt vermedi (timeout)", file=sys.stderr)
        process.kill()
        return None
    except Exception as e:
        print(f"Gemini CLI çağrısı sırasında hata: {e}", file=sys.stderr)
        return None




def _normalize_gemini_markdown(text: str) -> str:
    """Gemini çıktısındaki küçük biçimlendirme sorunlarını düzeltir.

    - "· 01.02.2003 (https://...)" → "· [01.02.2003](https://...)"
    - Ardışık yinelenen satırları tekilleştirir
    """
    import re

    # 1) Tarih + (URL) kalıbını tıklanabilir linke dönüştür
    text = re.sub(
        r"(·\s*)(\d{2}\.\d{2}\.\d{4})\s*\((https?://[^\)]+)\)",
        r"\1[\2](\3)",
        text,
    )

    # 2) Ardışık aynı satırları kaldır
    lines = text.splitlines()
    deduped_lines = []
    last = None
    for line in lines:
        if line != last:
            deduped_lines.append(line)
        last = line
    return "\n".join(deduped_lines).strip()


_markdown_console: Optional[Any] = None


def _wrap_markdown_text(markdown_text: str) -> str:
    """Markdown metnini sözcük bölünmeden terminal genişliğine göre sarar."""
    try:
        columns = shutil.get_terminal_size(fallback=(100, 24)).columns
    except Exception:
        columns = 100

    width = max(60, min(columns, 140)) - 2
    width = max(width, 40)

    wrapped_lines = []
    in_code_block = False
    fence = None

    lines = markdown_text.splitlines()
    for line in lines:
        stripped = line.lstrip()

        if stripped.startswith("```"):
            if not in_code_block:
                fence = stripped
                in_code_block = True
            elif fence == stripped or stripped.startswith("```"):
                in_code_block = False
            wrapped_lines.append(line)
            continue

        if in_code_block or not stripped:
            wrapped_lines.append(line)
            continue

        if stripped.startswith("#") or stripped.startswith(">"):
            wrapped_lines.append(line)
            continue

        indent_len = len(line) - len(stripped)
        indent = line[:indent_len]

        bullet_match = re.match(r"([\*\-\+•]\s+)", stripped)
        number_match = re.match(r"((?:\d+[\.\)]|[IVXLCDM]+\.)\s+)", stripped, flags=re.IGNORECASE)

        wrapper_kwargs = {
            "width": width,
            "break_long_words": False,
            "break_on_hyphens": False,
        }

        if bullet_match:
            prefix = bullet_match.group(0)
            content = stripped[len(prefix):].strip()
            wrapper = textwrap.TextWrapper(
                initial_indent=indent + prefix,
                subsequent_indent=indent + " " * len(prefix),
                **wrapper_kwargs,
            )
            wrapped_lines.extend(wrapper.fill(content).splitlines() if content else [indent + prefix.rstrip()])
            continue

        if number_match:
            prefix = number_match.group(0)
            content = stripped[len(prefix):].strip()
            wrapper = textwrap.TextWrapper(
                initial_indent=indent + prefix,
                subsequent_indent=indent + " " * len(prefix),
                **wrapper_kwargs,
            )
            wrapped_lines.extend(wrapper.fill(content).splitlines() if content else [indent + prefix.rstrip()])
            continue

        wrapper = textwrap.TextWrapper(
            initial_indent=indent,
            subsequent_indent=indent,
            **wrapper_kwargs,
        )
        wrapped_lines.extend(wrapper.fill(stripped).splitlines())

    return "\n".join(wrapped_lines)


def _display_markdown_viewer(markdown_text: str) -> None:
    """Gemini çıktısını terminalde Markdown olarak render eder."""
    if not markdown_text:
        return

    formatted_text = _wrap_markdown_text(markdown_text)

    if Console is None or Markdown is None or not sys.stdout.isatty():
        # Rich mevcut değilse veya çıktı başka bir programa yönlendirilmişse düz metin yazdır
        print(formatted_text)
        return

    global _markdown_console
    if _markdown_console is None:
        _markdown_console = Console(soft_wrap=False)

    _markdown_console.print(Markdown(formatted_text), soft_wrap=False)


def _process_gemini_output(
    entries: List[Dict],
    mode: Optional[str] = None,
    input_str: str = "",
    custom_prompt: Optional[str] = None,
    output_file: Optional[str] = None,
    use_flash: bool = False,
    time_filter: Optional[str] = None,
    filters: Optional[List[str]] = None,
    filter_external_urls: bool = False,
) -> Optional[str]:
    """Gemini çıktısını oluşturur, stdout'a yazdırır ve istenirse dosyaya kaydeder
    
    Args:
        entries: Entry listesi
        mode: 'summary' veya 'blog' (custom_prompt verilmişse None olabilir)
        input_str: Input string (başlık veya URL)
        custom_prompt: Özel prompt (verilmişse mode yerine kullanılır)
        output_file: MD dosyası yolu (verilirse dosyaya kaydeder)
        use_flash: Flash modelini kullan (daha hızlı, daha düşük kalite)
        time_filter: Kullanılan zaman filtresi (varsa)
        filters: Aktif içerik filtreleri listesi (varsa)
        filter_external_urls: Yalnızca Ekşi Sözlük dışı linklerin bulunduğu entry'lerin dahil edilip edilmediği
    
    Returns:
        Kaydedilen dosya yolu (eğer kaydedildiyse), None başarısız
    """
    if not entries:
        print("Uyarı: Entry bulunamadı, Gemini çıktısı oluşturulamadı", file=sys.stderr)
        return None
    
    # Prompt seç
    if custom_prompt:
        prompt = custom_prompt
        mode_name = 'özel prompt'
    elif mode == 'summary':
        prompt = GEMINI_SUMMARY_PROMPT
        mode_name = 'özet'
    elif mode == 'blog':
        prompt = GEMINI_BLOG_PROMPT
        mode_name = 'blog yazısı'
    else:
        print(f"Hata: Geçersiz mod veya prompt belirtilmemiş: {mode}", file=sys.stderr)
        return None
    
    # JSON verisini hazırla
    output_data = {
        'scrape_info': {
            'timestamp': datetime.now().isoformat(),
            'total_entries': len(entries),
            'input': input_str,
            'time_filter': time_filter,
            'filters': filters or [],
            'filter_external_urls': filter_external_urls
        },
        'entries': entries
    }
    json_data = json.dumps(output_data, ensure_ascii=False, indent=2)
    
    # Gemini çıktısını al
    print(f"Gemini ile {mode_name} oluşturuluyor...", file=sys.stderr)
    gemini_output = _generate_gemini_output(json_data, prompt, use_flash=use_flash)
    
    if not gemini_output:
        return None
    
    # Çıktıyı normalize et ve stdout'a yazdır
    normalized_output = _normalize_gemini_markdown(gemini_output)
    _display_markdown_viewer(normalized_output)
    
    # Eğer output_file belirtilmişse, MD dosyasına kaydet
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(normalized_output)
            print(f"Gemini çıktısı kaydedildi: {output_file}", file=sys.stderr)
            return output_file
        except Exception as e:
            print(f"Hata: Gemini çıktısı dosyaya yazılamadı: {e}", file=sys.stderr)
            return None
    
    return ""


def main():
    parser = argparse.ArgumentParser(
        description='Ekşi Sözlük Scraper: başlık veya entry URL\'sinden JSON/CSV/Markdown çıktı üretir.',
        formatter_class=CompactHelpFormatter,
        epilog='Daha fazla örnek: https://github.com/erenseymen/eksisozluk-scraper#readme'
    )
    
    parser.add_argument('input', nargs='?', help='Başlık adı veya entry URL\'si')
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}', help='Versiyonu göster ve çık')
    parser.add_argument('-d', '--days', type=int, help='Son N günü tara')
    parser.add_argument('-w', '--weeks', type=int, help='Son N haftayı tara')
    parser.add_argument('-m', '--months', type=int, help='Son N ayı tara')
    parser.add_argument('-y', '--years', type=int, help='Son N yılı tara')
    parser.add_argument('-s', '--start', dest='start_datetime', type=_parse_cli_datetime,
                        help=f"Başlangıç tarihini ayarla ({CLI_DATE_INPUT_EXAMPLE})")
    parser.add_argument('-e', '--end', dest='end_datetime', type=_parse_cli_datetime,
                        help=f"Bitiş tarihini ayarla ({CLI_DATE_INPUT_EXAMPLE})")
    parser.add_argument('-D', '--delay', type=float, default=0.0, help='İstekler arası bekleme (s)')
    parser.add_argument('-R', '--max-retries', type=int, default=3, help='Maksimum tekrar denemesi')
    parser.add_argument('-T', '--retry-delay', type=float, default=1.0, help='Denemeler arası bekleme (s)')
    parser.add_argument('-n', '--max-entries', type=int, help='Toplanacak maksimum entry')
    parser.add_argument('--output', '-o', help='Çıktı dosyası (.json/.csv/.md); yoksa stdout')
    parser.add_argument('-B', '--no-bkz', action='store_true', help='Referans edilen entry\'leri atla')
    parser.add_argument('--fetch', action='store_true', help='Harici içerikleri indir (URL ve YouTube)')
    parser.add_argument('-f', '--filter', dest='filters', action='append', metavar='KELIME', help='Entry içeriğini kelimeye göre filtrele (tekrar edilebilir)')
    parser.add_argument('-u', '--filter-urls', dest='filter_urls', action='store_true', help='Yalnızca harici URL içeren entry\'ler')
    parser.add_argument('-r', '--reverse', action='store_true', help='Sayfaları tersten tara')
    
    # Gemini CLI entegrasyonu grubu
    gemini_group = parser.add_argument_group('Gemini CLI', 'AI destekli çıktı seçenekleri (geminicli.com)')
    gemini_group.add_argument('-z', '--ozet', dest='gemini_summary', action='store_true', help='Gemini ile özet üret')
    gemini_group.add_argument('-b', '--blog', dest='gemini_blog', action='store_true', help='Gemini ile blog üret')
    gemini_group.add_argument('--prompt', '-p', dest='gemini_prompt', help='Gemini\'ye özel prompt gönder')
    gemini_group.add_argument('-F', '--flash', dest='flash', action='store_true', help='Gemini flash modelini kullan')
    
    # Enable tab completion if argcomplete is available
    if argcomplete:
        argcomplete.autocomplete(parser)
    
    args = parser.parse_args()
    
    # Input kontrolü - --version kullanıldıysa buraya gelmez (argparse otomatik çıkar)
    if not args.input:
        parser.error('input argümanı gereklidir (başlık adı veya entry URL\'si)')

    # Mutually exclusive time filters kontrolü
    relative_filters = any([args.days, args.weeks, args.months, args.years])
    absolute_filters = any([args.start_datetime, args.end_datetime])
    if relative_filters and absolute_filters:
        parser.error("Mutlak tarih aralığı (--start/--end) ile relativ filtreler (--days/--weeks/--months/--years) birlikte kullanılamaz")

    if args.start_datetime and args.end_datetime and args.start_datetime > args.end_datetime:
        parser.error("Başlangıç tarihi, bitiş tarihinden büyük olamaz")
    
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
    
    # Gemini istemi istendiğinde CLI kontrolü (entry indirme öncesinde)
    gemini_requested = any([
        bool(args.gemini_summary),
        bool(args.gemini_blog),
        args.gemini_prompt is not None,
    ])
    if gemini_requested and not _get_gemini_cli_path():
        print("Hata: Gemini CLI bulunamadı. Gemini özelliklerini kullanmak için 'gemini' komutunu kurmalısınız.", file=sys.stderr)
        print("Kurulum için talimatlar: https://geminicli.com/ adresini ziyaret edin.", file=sys.stderr)
        sys.exit(1)

    # Scraper oluştur
    scraper = EksisozlukScraper(
        delay=args.delay,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        output_file=args.output,
        max_entries=args.max_entries,
        fetch_referenced=not args.no_bkz,
        fetch_external=args.fetch,
        content_filters=args.filters,
        filter_external_urls=args.filter_urls,
        reverse=args.reverse,
        start_datetime=args.start_datetime,
        end_datetime=args.end_datetime,
    )
    
    if scraper.entry_filters:
        filters_display = ', '.join(scraper.entry_filters)
        print(f"İçerik filtreleri aktif: {filters_display}", file=sys.stderr)
    if scraper.filter_external_urls:
        print("URL filtresi aktif: Yalnızca Ekşi Sözlük dışına ait link içeren entry'ler getirilecek", file=sys.stderr)
    
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
                # Entry'leri yeniden sırala (field order)
                reordered_entries = scraper._reorder_entries(sorted_entries)
                output_data = {
                    'scrape_info': {
                        'timestamp': (scraper.scrape_start_time or datetime.now()).isoformat(),
                        'total_entries': len(reordered_entries),
                        'input': scraper.scrape_input or args.input,
                        'time_filter': scraper.scrape_time_filter or time_filter_string,
                        'filters': scraper.entry_filters,
                        'filter_external_urls': scraper.filter_external_urls
                    },
                    'entries': reordered_entries
                }
                output_json = json.dumps(output_data, ensure_ascii=False, indent=2)
                print(output_json)
                print(f"O ana kadar toplanan {len(reordered_entries)} entry terminale yazdırıldı (tarihe göre sıralanmış)", file=sys.stderr)
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
                # Entry'leri yeniden sırala (field order)
                reordered_entries = scraper._reorder_entries(sorted_entries)
                output_data = {
                    'scrape_info': {
                        'timestamp': (scraper.scrape_start_time or datetime.now()).isoformat(),
                        'total_entries': len(reordered_entries),
                        'input': scraper.scrape_input or args.input,
                        'time_filter': scraper.scrape_time_filter or time_filter_string,
                        'filters': scraper.entry_filters,
                        'filter_external_urls': scraper.filter_external_urls
                    },
                    'entries': reordered_entries
                }
                output_json = json.dumps(output_data, ensure_ascii=False, indent=2)
                print("\n" + output_json)
                print(f"O ana kadar toplanan {len(reordered_entries)} entry terminale yazdırıldı (tarihe göre sıralanmış)", file=sys.stderr)
        
        sys.exit(0)
    
    # Gemini modu varsa çıktıyı Gemini ile işle
    gemini_mode = None
    if args.gemini_prompt:
        # Özel prompt kullan
        gemini_mode = None  # Custom prompt kullanılacak
    elif args.gemini_summary:
        gemini_mode = 'summary'
    elif args.gemini_blog:
        gemini_mode = 'blog'
    
    if gemini_mode or args.gemini_prompt:
        # Entry'leri tarihe göre sırala
        sorted_entries = scraper._sort_entries_by_date(entries)
        # Entry'leri yeniden sırala (field order)
        reordered_entries = scraper._reorder_entries(sorted_entries)
        
        # Eğer -o parametresi kullanıldıysa, Gemini çıktısı için MD dosyası oluştur
        gemini_output_file = None
        if args.output:
            # Output dosyasından MD dosyası adı oluştur
            output_path = args.output
            # Dosya uzantısını değiştir veya ekle
            if output_path.endswith('.json'):
                gemini_output_file = output_path[:-5] + '.md'
            elif output_path.endswith('.csv'):
                gemini_output_file = output_path[:-4] + '.md'
            elif output_path.endswith('.md') or output_path.endswith('.markdown'):
                # Zaten MD dosyası, gemini için ek bir dosya oluştur
                base_name = output_path.rsplit('.', 1)[0]
                gemini_output_file = f"{base_name}-gemini.md"
            else:
                # Uzantı yoksa veya bilinmeyen uzantıysa .md ekle
                gemini_output_file = f"{output_path}.gemini.md"
        
        # Gemini çıktısını oluştur ve stdout'a yazdır
        gemini_file = _process_gemini_output(
            reordered_entries,
            gemini_mode,
            args.input,
            custom_prompt=args.gemini_prompt,
            output_file=gemini_output_file,
            use_flash=args.flash,
            time_filter=scraper.scrape_time_filter or time_filter_string,
            filters=scraper.entry_filters,
            filter_external_urls=scraper.filter_external_urls
        )
        
        if gemini_file is None:
            print("Gemini işlemi başarısız oldu", file=sys.stderr)
            sys.exit(1)
        
        # Bash script uyumluluğu için dosya yollarını stderr'e yazdır (parse edilebilir format)
        if gemini_file:
            print(f"GEMINI_OUTPUT_FILE={gemini_file}", file=sys.stderr)
        if args.output:
            print(f"JSON_OUTPUT_FILE={args.output}", file=sys.stderr)
        
        # Gemini modu aktifse JSON çıktısı verme (sadece Gemini çıktısı yeterli)
        sys.exit(0)
    
    # Çıktıyı hazırla (output dosyası belirtilmemişse stdout'a yaz)
    if not args.output:
        # Entry'leri tarihe göre sırala
        sorted_entries = scraper._sort_entries_by_date(entries)
        # Entry'leri yeniden sırala (field order)
        reordered_entries = scraper._reorder_entries(sorted_entries)
        output_data = {
            'scrape_info': {
                'timestamp': datetime.now().isoformat(),
                'total_entries': len(reordered_entries),
                'input': args.input,
                'time_filter': scraper.scrape_time_filter or time_filter_string,
            'filters': scraper.entry_filters,
            'filter_external_urls': scraper.filter_external_urls
            },
            'entries': reordered_entries
        }
        
        # JSON olarak çıktı ver
        output_json = json.dumps(output_data, ensure_ascii=False, indent=2)
        print(output_json)
    elif args.output:
        # Output dosyası zaten incremental olarak yazıldı, sadece bilgi ver
        print(f"Harika! Toplam {len(entries)} entry {args.output} dosyasına kaydedildi", file=sys.stderr)
        # Bash script uyumluluğu için dosya yolunu stderr'e yazdır (parse edilebilir format)
        print(f"JSON_OUTPUT_FILE={args.output}", file=sys.stderr)


if __name__ == '__main__':
    main()

