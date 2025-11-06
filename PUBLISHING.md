# Publishing eksisozluk-scraper to PyPI

Bu rehber, paketi PyPI'ye yayınlamak için gereken adımları açıklar.

## Ön Hazırlık

1. **PyPI hesabı oluşturun:**
   - Test PyPI: https://test.pypi.org/
   - Production PyPI: https://pypi.org/
   - Her ikisinde de hesap oluşturun

2. **API Token oluşturun:**
   - PyPI'de hesap ayarlarından API token oluşturun
   - Token'ı `~/.pypirc` dosyasına kaydedin veya ortam değişkeni olarak kullanın

## Gerekli Paketleri Kurun

```bash
pip install build twine
```

## Paketi Oluşturun

```bash
# Kaynak dağıtımı (sdist) ve wheel oluştur
python -m build

# Oluşturulan paketler dist/ klasöründe olacak
ls dist/
```

## Test PyPI'ye Yükleyin (Önerilen)

Önce test PyPI'ye yükleyerek her şeyin çalıştığını doğrulayın:

```bash
# Test PyPI'ye yükle
python -m twine upload --repository testpypi dist/*

# Test PyPI'den kurulum yaparak test edin
pip install --index-url https://test.pypi.org/simple/ eksisozluk-scraper
```

## Production PyPI'ye Yükleyin

Her şey test PyPI'de çalışıyorsa, production'a yükleyin:

```bash
# Production PyPI'ye yükle
python -m twine upload dist/*
```

## Sürüm Güncelleme

Yeni bir sürüm yayınlamak için:

1. `setup.py` dosyasındaki `version` değerini güncelleyin
2. `pyproject.toml` dosyasındaki `version` değerini güncelleyin
3. Git tag oluşturun:
   ```bash
   git tag v1.1.1
   git push origin v1.1.1
   ```
4. Yeniden build edin ve yükleyin

## .pypirc Dosyası Örneği

`~/.pypirc` dosyası (opsiyonel, API token kullanıyorsanız):

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Notlar

- İlk yüklemeden sonra paket adı rezerve edilir ve başkaları kullanamaz
- Sürüm numaraları benzersiz olmalıdır (aynı sürüm iki kez yüklenemez)
- Test PyPI'deki paketler otomatik olarak silinmez, ancak production'da yayınlanmadan önce test etmek için idealdir

