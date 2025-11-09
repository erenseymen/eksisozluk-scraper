# Maintainer: Eren Seymen <>
pkgname=eksisozluk-scraper
pkgver=2.0.0
_cloudscraper_ver=1.2.71
pkgrel=1
pkgdesc="Terminal tabanlı Ekşi Sözlük scraper'ı. Çıktısı AI-friendly formatlarda: JSON (varsayılan), CSV ve Markdown."
arch=('any')
url="https://github.com/erenseymen/eksisozluk-scraper"
license=('GPL3')
depends=(
  'python'
  'python-beautifulsoup4'
  'python-argcomplete'
  'python-rich'
  'python-requests'
  'python-urllib3'
  'python-charset-normalizer'
  'python-idna'
  'python-requests-toolbelt'
  'python-pyparsing'
  'python-typing_extensions'
  'python-soupsieve'
)
makedepends=(
  'python-setuptools'
  'python-build'
  'python-installer'
  'python-wheel'
)
optdepends=('bash-completion: bash completion support')
source=(
  "$pkgname-$pkgver.tar.gz::https://github.com/erenseymen/eksisozluk-scraper/archive/v${pkgver}.tar.gz"
  "cloudscraper-${_cloudscraper_ver}.tar.gz::https://files.pythonhosted.org/packages/source/c/cloudscraper/cloudscraper-${_cloudscraper_ver}.tar.gz"
)
sha256sums=(
  '47a6bf12e6553ef9adbd3ced7207f199acaf715a978a527bb268b798a37814b0'
  '429c6e8aa6916d5bad5c8a5eac50f3ea53c9ac22616f6cb21b18dcc71517d0d3'
)

build() {
  cd "$srcdir/$pkgname-$pkgver"
  python -m build --wheel --no-isolation

  cd "$srcdir/cloudscraper-${_cloudscraper_ver}"
  python -m build --wheel --no-isolation
}

package() {
  local _python_version
  _python_version=$(python -c "import sys; print('{}.{}'.format(sys.version_info.major, sys.version_info.minor))")

  local _site_packages="$pkgdir/usr/lib/python${_python_version}/site-packages"

  cd "$srcdir/$pkgname-$pkgver"
  python -m installer --destdir="$pkgdir" "$srcdir/cloudscraper-${_cloudscraper_ver}"/dist/cloudscraper-*.whl
  python -m installer --destdir="$pkgdir" dist/eksisozluk_scraper-*.whl

  # Remove egg-info requires.txt to prevent automatic dependency detection
  rm -f "$pkgdir/usr/lib/python${_python_version}/site-packages/eksisozluk_scraper"*.egg-info/requires.txt 2>/dev/null || true
  
  # Install fish completion
  install -Dm644 completions/eksisozluk-scraper.fish \
    "$pkgdir/usr/share/fish/vendor_completions.d/eksisozluk-scraper.fish"
  
  # Install bash completion (use the pre-written file as fallback)
  install -d "$pkgdir/usr/share/bash-completion/completions"
  install -m644 debian/eksisozluk-scraper.bash-completion \
    "$pkgdir/usr/share/bash-completion/completions/eksisozluk-scraper" 2>/dev/null || true
  
  # Generate bash completion using argcomplete (overwrites the file if successful)
  # This requires the script to be installed first, so we do it after package installation
  # Use system argcomplete, not the one in pkgdir
  if [ -f "$pkgdir/usr/bin/eksisozluk-scraper" ]; then
    PYTHONPATH="$_site_packages" \
    PATH="$pkgdir/usr/bin:$PATH" \
      python -m argcomplete.register-python-argcomplete eksisozluk-scraper \
      > "$pkgdir/usr/share/bash-completion/completions/eksisozluk-scraper" 2>/dev/null || true
  fi
  
  # Install zsh completion (fallback)
  install -d "$pkgdir/usr/share/zsh/site-functions"
  install -m644 completions/_eksisozluk-scraper \
    "$pkgdir/usr/share/zsh/site-functions/_eksisozluk-scraper" 2>/dev/null || true
  
  # Generate zsh completion using argcomplete
  if [ -f "$pkgdir/usr/bin/eksisozluk-scraper" ]; then
    PYTHONPATH="$_site_packages" \
    PATH="$pkgdir/usr/bin:$PATH" \
      python -m argcomplete.register-python-argcomplete --shell=zsh eksisozluk-scraper \
      > "$pkgdir/usr/share/zsh/site-functions/_eksisozluk-scraper" 2>/dev/null || true
  fi
}

# vim:set ts=2 sw=2 et:

