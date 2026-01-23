Давай соберём полный список. Разобью по категориям.

## Базовая статистика

```python
def mean(data: list, column: str) -> float
def median(data: list, column: str) -> float
def std(data: list, column: str) -> float
def percentile(data: list, column: str, p: int) -> float
def current_percentile(data: list, column: str) -> int
    """В каком перцентиле текущее значение vs история"""
```

## Экстремумы и диапазоны

```python
def find_max(data: list, column: str) -> dict  # {value, date}
def find_min(data: list, column: str) -> dict
def find_local_maxima(data: list, column: str, window: int) -> list
def find_local_minima(data: list, column: str, window: int) -> list
def calculate_range(data: list, column: str) -> dict  # {min, max, range, current_position %}
def distance_from_ath(data: list, column: str) -> dict  # {ath, ath_date, current, drawdown %}
def distance_from_atl(data: list, column: str) -> dict
```

## Тренды и моментум

```python
def moving_average(data: list, column: str, window: int) -> list
def ema(data: list, column: str, window: int) -> list
def rate_of_change(data: list, column: str, periods: int) -> list
def trend_direction(data: list, column: str, window: int) -> str  # "up" | "down" | "sideways"
def trend_strength(data: list, column: str, window: int) -> float  # 0-1
def momentum(data: list, column: str, periods: int) -> float
def acceleration(data: list, column: str, periods: int) -> float  # изменение темпа
```

## Волатильность

```python
def volatility(data: list, column: str, window: int) -> float
def atr(data: list, window: int) -> float  # Average True Range
def bollinger_position(data: list, column: str, window: int) -> float  # где цена между бандами (-1 до +1)
def volatility_regime(data: list, column: str) -> str  # "low" | "normal" | "high" | "extreme"
```

## Корреляции и связи

```python
def correlation(data1: list, data2: list) -> float
def rolling_correlation(data1: list, data2: list, window: int) -> list
def correlation_matrix(datasets: dict) -> dict  # {"btc_price": [...], "mvrv": [...]} → матрица
def lead_lag(data1: list, data2: list, max_lag: int) -> dict  # кто опережает кого
def granger_causality(data1: list, data2: list) -> dict  # причинность
```

## Сравнения

```python
def compare_periods(data: list, period1: tuple, period2: tuple) -> dict
    # {period1_avg, period2_avg, change_pct, vol1, vol2}
def compare_to_history(data: list, column: str, current_window: int) -> dict
    # текущий период vs вся история
def yoy_change(data: list, column: str) -> float  # год к году
def mom_change(data: list, column: str) -> float  # месяц к месяцу
def compare_cycles(data: list, column: str, cycle_dates: list) -> dict
    # сравнить поведение в разных циклах
```

## Аномалии и паттерны

```python
def detect_anomalies(data: list, column: str, z_threshold: float) -> list
def detect_regime_change(data: list, column: str) -> list  # точки смены режима
def find_divergence(price: list, indicator: list) -> list  # дивергенции цена/индикатор
def find_similar_periods(data: list, column: str, window: int, top_n: int) -> list
    # найти похожие на текущий периоды в прошлом
def detect_breakout(data: list, column: str, lookback: int) -> dict
    # пробой уровня
```

## Распределение и вероятности

```python
def distribution_stats(data: list, column: str) -> dict
    # {skew, kurtosis, normality_test}
def value_at_risk(data: list, column: str, confidence: float) -> float
def probability_above(data: list, column: str, threshold: float) -> float
    # исторически как часто было выше threshold
def expected_range(data: list, column: str, days: int, confidence: float) -> dict
    # ожидаемый диапазон на N дней вперёд
```

## Крипто-специфичные

```python
def mvrv_zscore(mvrv_data: list) -> list
def realized_profit_loss(data: list) -> dict
def supply_in_profit(data: list) -> float  # % supply в прибыли
def hodl_waves(utxo_data: list) -> dict  # распределение по возрасту
def exchange_flow(data: list) -> dict  # приток/отток с бирж
def whale_activity(data: list, threshold: float) -> list
def funding_rate_signal(funding: list) -> str
def nvt_ratio(price: list, tx_volume: list) -> list
```

## Мета-анализ

```python
def summarize_metrics(metrics: dict) -> dict
    # сводка: сколько bullish/bearish/neutral сигналов
def consensus_signal(metrics: dict) -> str
    # общий сигнал на основе всех метрик
def contradictions(metrics: dict) -> list
    # какие метрики противоречат друг другу
def confidence_score(metrics: dict) -> float
    # насколько уверены в сигнале (0-1)
```

---