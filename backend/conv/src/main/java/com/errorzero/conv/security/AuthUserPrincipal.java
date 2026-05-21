package com.errorzero.conv.security;

import com.errorzero.conv.domain.AuthProvider;
import com.errorzero.conv.domain.UserRole;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.Collection;
import java.util.List;

public record AuthUserPrincipal(
        Long userId,
        String loginId,
        String email,
        String name,
        UserRole role,
        AuthProvider provider
) implements UserDetails {

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return List.of(new SimpleGrantedAuthority("ROLE_" + role.name()));
    }

    @Override
    public String getPassword() {
        return "";
    }

    @Override
    public String getUsername() {
        return loginId;
    }
}
