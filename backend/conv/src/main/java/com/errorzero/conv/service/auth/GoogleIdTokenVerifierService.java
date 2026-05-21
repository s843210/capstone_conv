package com.errorzero.conv.service.auth;

import com.errorzero.conv.config.GoogleAuthProperties;
import com.google.api.client.googleapis.auth.oauth2.GoogleIdToken;
import com.google.api.client.googleapis.auth.oauth2.GoogleIdTokenVerifier;
import com.google.api.client.googleapis.javanet.GoogleNetHttpTransport;
import com.google.api.client.json.gson.GsonFactory;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class GoogleIdTokenVerifierService {

    private final GoogleAuthProperties googleAuthProperties;

    public GoogleUserInfo verify(String idTokenString) {
        List<String> clientIds = googleAuthProperties.resolveClientIds();
        if (clientIds.isEmpty()) {
            throw new IllegalStateException("GOOGLE_CLIENT_IDS 설정이 필요합니다.");
        }

        try {
            GoogleIdTokenVerifier verifier = new GoogleIdTokenVerifier.Builder(
                    GoogleNetHttpTransport.newTrustedTransport(),
                    GsonFactory.getDefaultInstance()
            )
                    .setAudience(clientIds)
                    .build();

            GoogleIdToken idToken = verifier.verify(idTokenString);
            if (idToken == null) {
                throw new BadCredentialsException("Google ID Token이 올바르지 않습니다.");
            }

            return toUserInfo(idToken.getPayload());
        } catch (BadCredentialsException e) {
            throw e;
        } catch (Exception e) {
            throw new BadCredentialsException("Google ID Token 검증에 실패했습니다.", e);
        }
    }

    private GoogleUserInfo toUserInfo(GoogleIdToken.Payload payload) {
        String subject = normalize(payload.getSubject());
        String email = normalize(payload.getEmail());
        String name = normalize((String) payload.get("name"));
        String hostedDomain = normalize(payload.getHostedDomain());

        if (subject == null) {
            throw new BadCredentialsException("Google 사용자 식별값이 없습니다.");
        }
        if (email == null || !Boolean.TRUE.equals(payload.getEmailVerified())) {
            throw new BadCredentialsException("검증된 Google 이메일이 필요합니다.");
        }

        String allowedDomain = googleAuthProperties.resolveAllowedDomain();
        if (allowedDomain != null && !allowedDomain.equals(hostedDomain)) {
            throw new BadCredentialsException("허용된 Google Workspace 도메인이 아닙니다.");
        }

        if (name == null) {
            name = email;
        }

        return new GoogleUserInfo(subject, email, name, hostedDomain);
    }

    private String normalize(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }
}
