package com.errorzero.conv.controller;

import com.errorzero.conv.config.WeatherProperties;
import com.errorzero.conv.domain.DailyContext;
import com.errorzero.conv.dto.WeatherContextBackfillResponseDto;
import com.errorzero.conv.dto.WeatherContextJobResponseDto;
import com.errorzero.conv.service.weather.WeatherContextService;
import com.errorzero.conv.service.weather.WeatherSnapshot;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/admin/context/weather")
@RequiredArgsConstructor
@Validated
@Tag(name = "Weather Context Admin API", description = "daily_context 날씨 적재/백필 관리 API")
public class WeatherContextAdminController {

    private final WeatherContextService weatherContextService;
    private final WeatherProperties weatherProperties;

    @Operation(summary = "단건 날씨 적재", description = "targetDate 기준으로 날씨를 조회해 daily_context에 upsert합니다.")
    @PostMapping
    public ResponseEntity<WeatherContextJobResponseDto> syncWeather(
            @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate targetDate,
            @RequestParam(defaultValue = "false") boolean dryRun
    ) {
        String runId = UUID.randomUUID().toString();
        LocalDate effectiveTargetDate = targetDate != null
                ? targetDate
                : LocalDate.now(ZoneId.of(weatherProperties.getScheduleZone())).plusDays(1);

        if (dryRun) {
            WeatherSnapshot snapshot = weatherContextService.fetchWeatherWithRetry(effectiveTargetDate);
            return ResponseEntity.ok(WeatherContextJobResponseDto.builder()
                    .runId(runId)
                    .status("DRY_RUN")
                    .targetDate(effectiveTargetDate)
                    .dryRun(true)
                    .avgTempC(snapshot.avgTempC())
                    .precipitationMm(snapshot.precipitationMm())
                    .isRain(snapshot.isRain())
                    .message("DB 저장 없이 날씨 조회만 수행했습니다.")
                    .build());
        }

        DailyContext saved = weatherContextService.upsertWeatherContext(effectiveTargetDate);
        return ResponseEntity.ok(WeatherContextJobResponseDto.builder()
                .runId(runId)
                .status("SUCCESS")
                .targetDate(saved.getTargetDate())
                .dryRun(false)
                .avgTempC(saved.getAvgTempC())
                .precipitationMm(saved.getPrecipitationMm())
                .isRain(saved.getIsRain())
                .updatedAt(saved.getUpdatedAt())
                .message("daily_context upsert 완료")
                .build());
    }

    @Operation(summary = "기간 백필", description = "from~to 기간의 날씨 데이터를 순차 적재합니다.")
    @PostMapping("/backfill")
    public ResponseEntity<WeatherContextBackfillResponseDto> backfillWeather(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            @RequestParam(defaultValue = "365") @Max(value = 3660, message = "maxDays는 3660 이하여야 합니다") int maxDays
    ) {
        if (from.isAfter(to)) {
            throw new IllegalArgumentException("from 날짜는 to 날짜보다 늦을 수 없습니다.");
        }

        long totalDays = from.datesUntil(to.plusDays(1)).count();
        if (totalDays > maxDays) {
            throw new IllegalArgumentException("요청 기간이 너무 깁니다. maxDays를 늘리거나 기간을 줄여주세요.");
        }

        String runId = UUID.randomUUID().toString();
        int successCount = 0;
        int failureCount = 0;
        List<String> errors = new ArrayList<>();

        LocalDate cursor = from;
        while (!cursor.isAfter(to)) {
            try {
                weatherContextService.upsertWeatherContext(cursor);
                successCount++;
            } catch (Exception ex) {
                failureCount++;
                if (errors.size() < 20) {
                    errors.add(cursor + " => " + ex.getMessage());
                }
            }
            cursor = cursor.plusDays(1);
        }

        String status = failureCount == 0 ? "SUCCESS" : (successCount == 0 ? "FAILED" : "PARTIAL_SUCCESS");

        return ResponseEntity.ok(WeatherContextBackfillResponseDto.builder()
                .runId(runId)
                .status(status)
                .from(from)
                .to(to)
                .successCount(successCount)
                .failureCount(failureCount)
                .errors(errors)
                .build());
    }
}
