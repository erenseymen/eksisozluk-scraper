%global python3_sitelib %(python3 -c "import sys; print('/usr/lib/python' + str(sys.version_info.major) + '.' + str(sys.version_info.minor) + '/site-packages')" 2>/dev/null || echo "%{_usr}/lib/python3/site-packages")

# Disable automatic Python dependency detection to use explicit Fedora package names
%define __find_requires %{nil}
%define __find_provides %{nil}

Name:           eksisozluk-scraper
Version:        2.0.1
Release:        1%{?dist}
Summary:        Ekşi Sözlük Scraper - AI-friendly output üreten terminal tabanlı scraper

License:        GPL-3.0-or-later
URL:            https://github.com/erenseymen/eksisozluk-scraper
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
Requires:       python3 >= 3.8
Requires:       python3-cloudscraper
Requires:       python3-beautifulsoup4
Requires:       python3-argcomplete

%description
Terminal tabanlı Ekşi Sözlük scraper'ı. Çıktısı AI-friendly formatlarda:
JSON (varsayılan), CSV ve Markdown.

Özellikler:
- Terminal tabanlı CLI arayüzü
- Çoklu çıktı formatı desteği (JSON, CSV, Markdown)
- Format otomatik tespiti (dosya uzantısından)
- Başlık bazlı tüm entry scraping
- Zaman aralığına göre filtreleme (gün/hafta/ay/yıl)
- Tab completion desteği (bash/zsh/fish)
- Rate limiting ve otomatik retry mekanizması

%prep
%setup -q

%build
python3 setup.py build

%install
python3 setup.py install --skip-build --root %{buildroot} --prefix %{_prefix} --install-lib %{python3_sitelib} --install-scripts %{_bindir}

# Remove requires.txt from egg-info to prevent automatic dependency detection
rm -f %{buildroot}%{python3_sitelib}/eksisozluk_scraper*.egg-info/requires.txt 2>/dev/null || true

# Remove .pyc files to avoid Python ABI version lock (Python will compile them at runtime)
rm -rf %{buildroot}%{python3_sitelib}/__pycache__ 2>/dev/null || true

# Replace setuptools-generated entry point script with a simple one that doesn't require setuptools
# Script will dynamically find the module location
cat > %{buildroot}%{_bindir}/eksisozluk-scraper << 'EOFScript'
#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import importlib.util
import os

# Dynamically find the module path
for path in sys.path:
    module_path = os.path.join(path, 'eksisozluk_scraper.py')
    if os.path.exists(module_path):
        spec = importlib.util.spec_from_file_location("eksisozluk_scraper", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.exit(module.main())

# If not found, try direct import
try:
    import eksisozluk_scraper
    sys.exit(eksisozluk_scraper.main())
except ImportError:
    print("Error: Could not find eksisozluk_scraper module", file=sys.stderr)
    sys.exit(1)
EOFScript
chmod 755 %{buildroot}%{_bindir}/eksisozluk-scraper

# Install bash completion
mkdir -p %{buildroot}%{_sysconfdir}/bash_completion.d
install -m 644 debian/eksisozluk-scraper.bash-completion \
    %{buildroot}%{_sysconfdir}/bash_completion.d/eksisozluk-scraper

# Install fish completion
mkdir -p %{buildroot}%{_datadir}/fish/vendor_completions.d
install -m 644 completions/eksisozluk-scraper.fish \
    %{buildroot}%{_datadir}/fish/vendor_completions.d/eksisozluk-scraper.fish

%post
# Register bash completion if bash-completion is available
if [ -f %{_sysconfdir}/bash_completion ]; then
    if command -v register-python-argcomplete >/dev/null 2>&1; then
        mkdir -p %{_datadir}/bash-completion/completions 2>/dev/null || true
        register-python-argcomplete eksisozluk-scraper > %{_datadir}/bash-completion/completions/eksisozluk-scraper 2>/dev/null || true
    fi
fi

%postun
# Clean up bash completion
if [ -f %{_datadir}/bash-completion/completions/eksisozluk-scraper ]; then
    rm -f %{_datadir}/bash-completion/completions/eksisozluk-scraper
fi

%files
%{_bindir}/eksisozluk-scraper
%{python3_sitelib}/eksisozluk_scraper.py
%{python3_sitelib}/eksisozluk_scraper*.egg-info
%exclude %{python3_sitelib}/eksisozluk_scraper*.egg-info/requires.txt
%exclude %{python3_sitelib}/eksisozluk_scraper*.egg-info/entry_points.txt
%config(noreplace) %{_sysconfdir}/bash_completion.d/eksisozluk-scraper
%{_datadir}/fish/vendor_completions.d/eksisozluk-scraper.fish

%changelog
* Mon Nov 10 2025 Eren Seymen - 2.0.0-1
- 2.0.0 release

* Mon Nov 04 2025 Eren Seymen - 1.1.0-1
- Initial RPM package release

