package com.errorzero.conv.repository;

import com.errorzero.conv.domain.AppUser;
import com.errorzero.conv.domain.AuthProvider;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface AppUserRepository extends JpaRepository<AppUser, Long> {

    Optional<AppUser> findByLoginId(String loginId);

    Optional<AppUser> findByEmail(String email);

    Optional<AppUser> findByProviderAndProviderUserId(AuthProvider provider, String providerUserId);
}
