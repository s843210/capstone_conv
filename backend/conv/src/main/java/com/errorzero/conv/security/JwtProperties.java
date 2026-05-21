package com.errorzero.conv.security;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "app.jwt")
public class JwtProperties {

    private String secret = "local-development-jwt-secret-change-this-before-release";
    private String issuer = "campus-store";
    private long expirationMinutes = 120L;
}
