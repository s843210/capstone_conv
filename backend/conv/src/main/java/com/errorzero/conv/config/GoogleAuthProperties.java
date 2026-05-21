package com.errorzero.conv.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.List;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "app.auth.google")
public class GoogleAuthProperties {

    private String clientIds = "";
    private String allowedDomain = "";

    public List<String> resolveClientIds() {
        if (clientIds == null || clientIds.isBlank()) {
            return List.of();
        }

        return Arrays.stream(clientIds.split(","))
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .toList();
    }

    public String resolveAllowedDomain() {
        if (allowedDomain == null || allowedDomain.isBlank()) {
            return null;
        }
        return allowedDomain.trim();
    }
}
