package com.errorzero.conv.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
public class HolidayClientConfig {

    @Bean
    public RestClient holidayRestClient(HolidayProperties holidayProperties) {
        int timeoutMillis = Math.max(holidayProperties.getTimeoutSec(), 1) * 1000;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(timeoutMillis);
        requestFactory.setReadTimeout(timeoutMillis);

        return RestClient.builder()
                .baseUrl(holidayProperties.getBaseUrl())
                .requestFactory(requestFactory)
                .build();
    }
}
