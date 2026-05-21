package com.errorzero.conv.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "app.auth.admin")
public class AdminAccountProperties {

    private String loginId = "";
    private String password = "";
    private String name = "admin";
    private String email = "";
}
