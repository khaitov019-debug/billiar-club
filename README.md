# BILYARD CLUB — Android APK

Android uchun Kivy + Buildozer loyihasi.

## Funksiyalar
- 5 ta Billiard
- 3 ta Tennis
- real-time sekundomer
- Pauza / Davom ettirish
- Stolni tugatish va hisoblash
- Mahsulot qo'shish
- Kunlik hisobot
- Sozlamalar
- Ma'lumotlarni telefonda saqlash

## GitHub
Ushbu 5 ta faylni repository root qismiga joylang:

1. `main.py`
2. `buildozer.spec`
3. `requirements.txt`
4. `.gitignore`
5. `README.md`

## APK
Buildozer o'rnatilgan Linux/WSL muhitida:

```bash
buildozer android debug
```

Tayyor APK odatda `bin/` papkasida chiqadi.

> GitHubning o'zi APKni avtomatik yaratmaydi. APK uchun GitHub Actions yoki Buildozer ishlatiladi.
