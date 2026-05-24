package com.errorzero.conv.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 글로벌 웹 설정.
 * CORS 정책을 한 곳에서 관리하여 각 Controller에서 @CrossOrigin 중복을 제거합니다.
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins(
                        "http://localhost:5173",
                        "http://localhost:8081",
                        "http://localhost:19006",
                        "http://10.63.213.230:8081",
                        "http://10.63.213.230:19006",
                        "http://13.124.92.75"
                )
                .allowedMethods("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }
}
