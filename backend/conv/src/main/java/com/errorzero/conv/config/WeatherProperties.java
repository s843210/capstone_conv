package com.errorzero.conv.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "app.weather")
public class WeatherProperties {

    private boolean enabled = false;
    private String baseUrl = "https://api.openweathermap.org";
    private String forecastPath = "/data/2.5/forecast";
    private String apiKey = "";
    private double latitude = 37.5665;
    private double longitude = 126.9780;
    private int timeoutSec = 10;
    private int retryCount = 3;
    private long retryBackoffMillis = 500L;
    private String scheduleCron = "0 40 17 * * *";
    private String scheduleZone = "Asia/Seoul";
}
