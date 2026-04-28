package com.errorzero.conv.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "app.holiday")
public class HolidayProperties {

    private boolean enabled = true;
    private boolean includeWeekend = true;
    private boolean apiEnabled = true;
    private String baseUrl = "https://date.nager.at";
    private String publicHolidayPath = "/api/v3/PublicHolidays/{year}/{countryCode}";
    private String countryCode = "KR";
    private int timeoutSec = 8;
    private int retryCount = 2;
    private long retryBackoffMillis = 300L;
}
