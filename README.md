# Wirtualny Tauron

Custom integration dla **Home Assistant**: emulator magazynu energii dla
prosumenta rozliczanego w **starym systemie opustów (net-metering)**.

Pozwala podejrzeć w panelu Energii „wirtualną baterię", której stan odpowiada
ilości energii **do odebrania** u sprzedawcy (Tauron / e-Dystrybucja):

```
stan_magazynu = stan_początkowy + oddana × współczynnik − pobrana
```

- każda oddana do sieci kWh **dopisuje** `współczynnik` kWh (0,8 dla instalacji ≤ 10 kW, 0,7 powyżej),
- każda pobrana kWh **zabiera** 1 kWh,
- stan początkowy wpisujesz z faktury / portalu e-Dystrybucja i w każdej chwili możesz go skorygować usługą.

## Instalacja

### HACS (custom repository)
1. HACS → ⋮ → *Custom repositories* → dodaj `RoSulek1/wirtualny-tauron` (kategoria: *Integration*).
2. Zainstaluj **Wirtualny Tauron** i zrestartuj Home Assistant.

### Ręcznie
Skopiuj katalog `custom_components/wirtualny_tauron` do katalogu `config/custom_components/` w Twojej instancji HA i zrestartuj HA.

## Konfiguracja

1. **Ustawienia → Urządzenia i usługi → Dodaj integrację → Wirtualny Tauron**.
2. Wybierz:
   - encję **energii oddanej** do sieci (kWh, `total_increasing`) — np. `sensor.zamel_mew_..._total_reverse_active_energy`,
   - encję **energii pobranej** z sieci (kWh, `total_increasing`) — np. `sensor.zamel_mew_..._total_forward_active_energy`,
   - **współczynnik** (domyślnie `0.8`),
   - **stan początkowy magazynu** (kWh do odebrania z ostatniej faktury; można też zostawić 0 i ustawić później).

## Sensory

| Sensor | Opis |
|---|---|
| `sensor.wirtualny_tauron_magazyn` | stan wirtualnego magazynu (kWh) — podłącz w panelu Energii jako **magazyn energii** |
| `sensor.wirtualny_tauron_oddane_od_instalacji` | energia oddana od momentu instalacji / korekty (kWh) |
| `sensor.wirtualny_tauron_pobrane_od_instalacji` | energia pobrana od momentu instalacji / korekty (kWh) |

### Panel Energii
Ustawienia panelu Energii → sekcja **Magazyn energii domowego** → wybierz
`sensor.wirtualny_tauron_magazyn`. Bateria będzie się „ładować" o `0,8 kWh`
za każdą oddaną kWh i „rozładowywać" o `1 kWh` za każdą pobraną.

## Korekta stanu z faktury

Licznik Zamel/instalacji mierzy **przed** licznikiem sprzedawcy, więc rozliczenie
Taurona może się minimalnie różnić. Po każdej fakturze wyrównaj stan:

**Narzędzia deweloperskie → Akcje**:
```yaml
action: wirtualny_tauron.set_stored_energy
data:
  stored_energy: 1234.5   # kWh "do odebrania" z faktury
```

Usługa ustawia nową bazę i resetuje punkty odniesienia liczników źródłowych —
dalsze naliczanie jest od razu poprawne.

## Uwagi

- Stany przeżywają restarty HA (przechowywane w wpisie konfiguracji).
- Zmiana współczynnika lub encji źródłowych w **Opcjach** działa „od teraz" —
  aktualny stan magazynu jest zachowywany (rebase), historia nie jest przeliczana wstecz.
- Jeśli encja źródłowa jest chwilowo niedostępna, sensory pokazują ostatni
  poprawny stan (atrybut `stale: true`).
- Zerowanie licznika źródła (np. wymiana urządzenia) jest ignorowane (`max(0, …)`);
  po wymianie ustaw stan usługą `set_stored_energy`.

## Licencja

MIT
