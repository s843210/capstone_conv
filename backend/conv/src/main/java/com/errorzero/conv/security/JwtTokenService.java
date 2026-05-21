package com.errorzero.conv.security;

import com.errorzero.conv.domain.AppUser;
import com.errorzero.conv.domain.AuthProvider;
import com.errorzero.conv.domain.UserRole;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class JwtTokenService {

    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };

    private final JwtProperties jwtProperties;
    private final ObjectMapper objectMapper;

    public JwtTokenService(JwtProperties jwtProperties, ObjectMapper objectMapper) {
        this.jwtProperties = jwtProperties;
        this.objectMapper = objectMapper;
    }

    public String createToken(AppUser user) {
        Instant now = Instant.now();
        Instant expiresAt = now.plusSeconds(Math.max(jwtProperties.getExpirationMinutes(), 1L) * 60L);

        Map<String, Object> header = new LinkedHashMap<>();
        header.put("alg", "HS256");
        header.put("typ", "JWT");

        Map<String, Object> claims = new LinkedHashMap<>();
        claims.put("iss", jwtProperties.getIssuer());
        claims.put("sub", String.valueOf(user.getId()));
        claims.put("iat", now.getEpochSecond());
        claims.put("exp", expiresAt.getEpochSecond());
        claims.put("loginId", user.getLoginId());
        claims.put("email", user.getEmail());
        claims.put("name", user.getName());
        claims.put("role", user.getRole().name());
        claims.put("provider", user.getProvider().name());

        String signingInput = encodeJson(header) + "." + encodeJson(claims);
        return signingInput + "." + sign(signingInput);
    }

    public AuthUserPrincipal parseToken(String token) {
        String[] parts = token.split("\\.");
        if (parts.length != 3) {
            throw new IllegalArgumentException("JWT 형식이 올바르지 않습니다.");
        }

        String signingInput = parts[0] + "." + parts[1];
        String expectedSignature = sign(signingInput);
        if (!MessageDigest.isEqual(expectedSignature.getBytes(StandardCharsets.UTF_8), parts[2].getBytes(StandardCharsets.UTF_8))) {
            throw new IllegalArgumentException("JWT 서명이 올바르지 않습니다.");
        }

        Map<String, Object> claims = decodeJson(parts[1]);
        validateClaims(claims);

        return new AuthUserPrincipal(
                toLong(claims.get("sub")),
                toStringValue(claims.get("loginId")),
                toStringValue(claims.get("email")),
                toStringValue(claims.get("name")),
                UserRole.valueOf(toStringValue(claims.get("role"))),
                AuthProvider.valueOf(toStringValue(claims.get("provider")))
        );
    }

    private void validateClaims(Map<String, Object> claims) {
        String issuer = toStringValue(claims.get("iss"));
        if (!jwtProperties.getIssuer().equals(issuer)) {
            throw new IllegalArgumentException("JWT 발급자가 올바르지 않습니다.");
        }

        long expiresAt = toLong(claims.get("exp"));
        if (Instant.now().getEpochSecond() >= expiresAt) {
            throw new IllegalArgumentException("JWT가 만료되었습니다.");
        }
    }

    private String encodeJson(Map<String, Object> value) {
        try {
            return base64UrlEncode(objectMapper.writeValueAsBytes(value));
        } catch (Exception e) {
            throw new IllegalStateException("JWT JSON 생성에 실패했습니다.", e);
        }
    }

    private Map<String, Object> decodeJson(String encodedValue) {
        try {
            return objectMapper.readValue(base64UrlDecode(encodedValue), MAP_TYPE);
        } catch (Exception e) {
            throw new IllegalArgumentException("JWT payload를 읽을 수 없습니다.", e);
        }
    }

    private String sign(String value) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(jwtProperties.getSecret().getBytes(StandardCharsets.UTF_8), HMAC_ALGORITHM));
            return base64UrlEncode(mac.doFinal(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException("JWT 서명에 실패했습니다.", e);
        }
    }

    private String base64UrlEncode(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    private byte[] base64UrlDecode(String value) {
        return Base64.getUrlDecoder().decode(value);
    }

    private String toStringValue(Object value) {
        if (value == null) {
            return "";
        }
        return String.valueOf(value);
    }

    private long toLong(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        return Long.parseLong(toStringValue(value));
    }
}
