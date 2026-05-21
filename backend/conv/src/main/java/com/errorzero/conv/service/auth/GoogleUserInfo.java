package com.errorzero.conv.service.auth;

public record GoogleUserInfo(
        String subject,
        String email,
        String name,
        String hostedDomain
) {
}
