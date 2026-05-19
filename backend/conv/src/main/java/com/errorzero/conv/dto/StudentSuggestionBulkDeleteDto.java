package com.errorzero.conv.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
@NoArgsConstructor
public class StudentSuggestionBulkDeleteDto {

    @NotBlank(message = "writer는 필수입니다")
    private String writer;

    @NotEmpty(message = "ids는 최소 1개 이상 필요합니다")
    private List<Long> ids;
}
