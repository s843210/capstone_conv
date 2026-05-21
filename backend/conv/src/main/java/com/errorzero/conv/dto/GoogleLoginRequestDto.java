package com.errorzero.conv.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class GoogleLoginRequestDto {

    @NotBlank(message = "idToken은 필수입니다")
    private String idToken;
}
