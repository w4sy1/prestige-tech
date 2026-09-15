# Podpisy manifestów i baseline

Hash Checker i Integrity Monitor obsługują Ed25519 z osobnym zaufanym kluczem
publicznym. Instalacja ze źródeł: `python -m pip install -r requirements-signing.txt`.
W EXE wymagane biblioteki są dołączone.

Ustaw hasło sesji w GUI albo zmienną środowiskową `PRESTIGE_SIGNING_PASSWORD`
(minimum 12 bajtów). `keygen` wymaga nowych ścieżek `--private-key` i `--public-key`.
Klucz prywatny jest szyfrowany w formacie PKCS8. Nigdy nie dołączaj go do paczki
z raportami; przechowuj kopię w bezpiecznym miejscu.

Hash Checker:

```powershell
python app.py keygen --private-key private.pem --public-key public.pem
python app.py sign --manifest manifest.json --private-key private.pem --signature manifest.sig.json
python app.py verify-signature --manifest manifest.json --public-key public.pem --signature manifest.sig.json
```

W Integrity Monitor zamiast `--manifest` użyj `--baseline`.
W EXE poprzedź argumenty przez `--backend`.
Klucz publiczny musi pochodzić z zaufanego kanału. Poprawny podpis potwierdza
zgodność z tym kluczem, nie tożsamość osoby. Nie jest to podpis Authenticode EXE.
Zmiana treści lub niepasujący podpis daje wynik `ok: false` i kod wyjścia 2.

