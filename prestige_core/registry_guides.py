"""Krótkie opisy zatwierdzonych zmian rejestru dla osób nietechnicznych."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegistryGuide:
    operation: str
    level: str
    edition: str
    summary: str
    impact: str
    after: str


def completion_instructions(operation_id, backup_path, *, undone=False):
    """Czytelny wynik po zweryfikowanym zapisie lub cofnięciu HKCU."""
    guide = GUIDES[operation_id]
    if undone:
        return ("Co zrobiono: Przywrócono poprzednie ustawienie.\n"
                f"Jak sprawdzić: {guide.after}\n"
                "Jak cofnąć: Nie wykonuj ponownie cofnięcia tej samej kopii. "
                "Jeśli chcesz wrócić do zmienionego ustawienia, przygotuj nowy plan.\n"
                "Restart: Samo cofnięcie nie wymaga restartu do zapisania wartości; "
                "widok może wymagać ponownego otwarcia Eksploratora lub Windows.")
    restart = ("Uruchom ponownie Windows, aby ocenić efekt tej polityki."
               if operation_id == "REG-WRITE-013" else
               "Nie jest wymagany do zapisania wartości. Jeśli efekt nie pojawi się od razu, "
               "otwórz ponownie odpowiednie okno; niektóre ustawienia mogą wymagać ponownego logowania.")
    return (f"Co zrobiono: {guide.summary}\n"
            f"Jak sprawdzić: {guide.after}\n"
            "Jak cofnąć: W sekcji «Moje kopie zmian» wybierz tę operację i kliknij "
            f"«Cofnij wybraną zmianę». Kopia: {backup_path}\n"
            f"Restart: {restart}")


GUIDES = {
    "REG-WRITE-001": RegistryGuide("REG-WRITE-001", "Początkujący", "FREE",
        "Pokazuje końcówki nazw plików, np. .pdf i .exe.",
        "Ułatwia rozpoznanie typu pliku. Nie zmienia zawartości plików.",
        "Otwórz ponownie okno Eksploratora, jeśli zmiana nie pojawi się od razu."),
    "REG-WRITE-002": RegistryGuide("REG-WRITE-002", "Początkujący", "FREE",
        "Pokazuje zwykłe ukryte pliki i foldery.",
        "Na liście zobaczysz więcej pozycji; nic nie jest usuwane.",
        "W razie potrzeby otwórz ponownie okno folderu."),
    "REG-WRITE-003": RegistryGuide("REG-WRITE-003", "Początkujący", "FREE",
        "Włącza podgląd obsługiwanych plików w panelu Eksploratora.",
        "Podgląd może uruchamiać zainstalowane dodatki; otwieraj tylko zaufane pliki.",
        "Wybierz plik w panelu podglądu Eksploratora."),
    "REG-WRITE-004": RegistryGuide("REG-WRITE-004", "Początkujący", "PRO",
        "Dodaje pola wyboru obok plików.", "Ułatwia wybór wielu plików myszą.",
        "Sprawdź widok dowolnego folderu."),
    "REG-WRITE-005": RegistryGuide("REG-WRITE-005", "Średniozaawansowany", "PRO",
        "Włącza kreator udostępniania folderów.",
        "Zmienia sposób wyświetlania opcji udostępniania; sam niczego nie udostępnia.",
        "Sprawdź menu udostępniania wybranego folderu."),
    "REG-WRITE-006": RegistryGuide("REG-WRITE-006", "Początkujący", "PRO",
        "Pokazuje miniatury zdjęć zamiast samych ikon.",
        "Eksplorator może tworzyć lokalną pamięć podręczną miniatur.",
        "Otwórz folder ze zdjęciami."),
    "REG-WRITE-007": RegistryGuide("REG-WRITE-007", "Początkujący", "PRO",
        "Pokazuje podpowiedzi po wskazaniu pliku.",
        "Zmienia tylko widok informacji o pliku.", "Wskaż plik kursorem w Eksploratorze."),
    "REG-WRITE-008": RegistryGuide("REG-WRITE-008", "Średniozaawansowany", "PRO",
        "Wyróżnia kolorami pliki skompresowane lub szyfrowane przez NTFS.",
        "Nie szyfruje ani nie kompresuje plików.", "Sprawdź folder na woluminie NTFS."),
    "REG-WRITE-009": RegistryGuide("REG-WRITE-009", "Zaawansowany", "PRO",
        "Otwiera okna folderów w osobnym procesie Eksploratora.",
        "Może zwiększyć użycie pamięci i wymagać ponownego otwarcia okien.",
        "Uruchom nowe okno Eksploratora i sprawdź działanie."),
    "REG-WRITE-010": RegistryGuide("REG-WRITE-010", "Zaawansowany", "PRO",
        "Pokazuje chronione pliki systemowe w Eksploratorze.",
        "Łatwiej przypadkowo zmienić ważny plik; samo włączenie niczego nie usuwa.",
        "Nie modyfikuj tych plików bez kopii i konkretnej instrukcji."),
    "REG-WRITE-011": RegistryGuide("REG-WRITE-011", "Początkujący", "PRO",
        "Pokazuje małą ikonę typu pliku na miniaturze.",
        "Zmienia wygląd miniatur, nie treść plików.",
        "Otwórz folder z plikami obsługiwanymi przez miniatury."),
    "REG-WRITE-012": RegistryGuide("REG-WRITE-012", "Średniozaawansowany", "PRO",
        "Wyłącza zapisywanie i podpowiadanie poprzednich fraz w polu wyszukiwania Eksploratora plików.",
        "Nie wyłącza wyników internetowych w menu Start ani samej wyszukiwarki Windows. Wymaga wspieranej edycji Pro/Enterprise/Education.",
        "Wpisz frazę w polu wyszukiwania Eksploratora i sprawdź podpowiedzi po ponownym otwarciu."),
    "REG-WRITE-013": RegistryGuide("REG-WRITE-013", "Zaawansowany", "PRO",
        "Ukrywa Centrum powiadomień na pasku zadań.",
        "Możesz nie móc przejrzeć powiadomień, które pojawiły się podczas nieobecności. Wymaga wspieranej edycji Pro/Enterprise/Education.",
        "Uruchom Windows ponownie i sprawdź obszar powiadomień; cofnięcie przywraca poprzednią politykę."),
    "REG-WRITE-014": RegistryGuide("REG-WRITE-014", "Początkujący", "PRO",
        "Ukrywa krótkie fragmenty treści plików w widoku „Zawartość” Eksploratora.",
        "Zmienia wyłącznie sposób pokazywania zawartości, nie usuwa tekstu z plików. Wymaga wspieranej edycji Windows.",
        "W Eksploratorze przełącz widok na „Zawartość” i sprawdź opis plików."),
    "REG-WRITE-015": RegistryGuide("REG-WRITE-015", "Średniozaawansowany", "PRO",
        "Wyłącza tworzenie, odczytywanie i zapis ukrytych plików miniatur thumbs.db w folderach sieciowych.",
        "Miniatury zasobów sieciowych mogą ładować się wolniej. Nie usuwa istniejących plików thumbs.db.",
        "Otwórz folder sieciowy z obrazami i oceń szybkość wyświetlania miniatur."),
    "REG-WRITE-016": RegistryGuide("REG-WRITE-016", "Początkujący", "FREE",
        "Pokazuje pasek stanu u dołu okna Eksploratora plików.",
        "Zajmuje trochę miejsca w oknie, ale nie zmienia zawartości plików.",
        "Otwórz okno Eksploratora i sprawdź dolną krawędź."),
    "REG-WRITE-017": RegistryGuide("REG-WRITE-017", "Początkujący", "FREE",
        "Ustawia jasny motyw obsługujących go aplikacji Windows.",
        "Zmienia wygląd aplikacji, nie ich danych; część programów używa własnego motywu.",
        "Otwórz aplikację obsługującą motyw systemowy i sprawdź jej kolory."),
    "REG-WRITE-018": RegistryGuide("REG-WRITE-018", "Początkujący", "FREE",
        "Ustawia jasny motyw elementów interfejsu Windows.",
        "Zmienia wygląd systemu, nie wydajność ani zawartość plików.",
        "Sprawdź menu Start i pasek zadań po ponownym otwarciu."),
    "REG-WRITE-019": RegistryGuide("REG-WRITE-019", "Początkujący", "PRO",
        "Wyłącza efekt przezroczystości okien i powierzchni Windows.",
        "Interfejs może być czytelniejszy; nie obiecujemy mierzalnego przyspieszenia.",
        "Sprawdź wygląd menu Start i okien systemowych."),
    "REG-WRITE-020": RegistryGuide("REG-WRITE-020", "Początkujący", "FREE",
        "Pokazuje wybrany kolor akcentu na paskach tytułu i obramowaniach okien.",
        "Może ułatwić rozpoznanie aktywnego okna; nie zmienia danych ani szybkości komputera.",
        "Otwórz dwa okna i sprawdź kolor paska tytułu aktywnego okna."),
}
