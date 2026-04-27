package com.errorzero.conv.service.weather;

public record WeatherSnapshot(
        Double avgTempC,
        double precipitationMm,
        short isRain
) {
}
