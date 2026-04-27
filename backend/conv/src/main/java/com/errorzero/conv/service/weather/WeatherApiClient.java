package com.errorzero.conv.service.weather;

import java.time.LocalDate;

public interface WeatherApiClient {
    WeatherSnapshot fetchDailyWeather(LocalDate targetDate);
}
