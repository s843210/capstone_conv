package com.errorzero.conv.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
public class WeatherClientConfig {

    @Bean
    public RestClient weatherRestClient(WeatherProperties weatherProperties) {
        int timeoutMillis = Math.max(weatherProperties.getTimeoutSec(), 1) * 1000;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(timeoutMillis);
        requestFactory.setReadTimeout(timeoutMillis);

        return RestClient.builder()
                .baseUrl(weatherProperties.getBaseUrl())
                .requestFactory(requestFactory)
                .build();
    }
}
