package com.errorzero.conv.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class StudentSuggestionUpdateDto {

    @NotBlank(message = "writer는 필수입니다")
    @Size(max = 50, message = "writer는 50자 이하로 입력해 주세요")
    private String writer;

    @NotBlank(message = "title은 필수입니다")
    @Size(max = 100, message = "title은 100자 이하로 입력해 주세요")
    private String title;

    @NotBlank(message = "content는 필수입니다")
    private String content;
}
