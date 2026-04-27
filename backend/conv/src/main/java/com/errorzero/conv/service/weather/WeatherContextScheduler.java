package com.errorzero.conv.service.weather;

import com.errorzero.conv.config.WeatherProperties;
import com.errorzero.conv.domain.DailyContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.UUID;
import java.util.concurrent.locks.ReentrantLock;

@Slf4j
@Component
@RequiredArgsConstructor
public class WeatherContextScheduler {

    private final WeatherContextService weatherContextService;
    private final WeatherProperties weatherProperties;

    private final ReentrantLock runLock = new ReentrantLock();

    @Scheduled(cron = "${app.weather.schedule-cron:0 40 17 * * *}", zone = "${app.weather.schedule-zone:Asia/Seoul}")
    public void runDailyWeatherSync() {
        if (!weatherProperties.isEnabled()) {
            return;
        }

        if (!runLock.tryLock()) {
            log.warn("날씨 수집 스케줄 중복 실행 방지: 이전 작업이 아직 진행 중입니다.");
            return;
        }

        String runId = UUID.randomUUID().toString();
        Instant startedAt = Instant.now();

        try {
            LocalDate targetDate = LocalDate.now(ZoneId.of(weatherProperties.getScheduleZone())).plusDays(1);
            DailyContext saved = weatherContextService.upsertWeatherContext(targetDate);

            long durationMs = Duration.between(startedAt, Instant.now()).toMillis();
            log.info("날씨 컨텍스트 적재 성공: runId={}, targetDate={}, avgTempC={}, precipitationMm={}, isRain={}, durationMs={}",
                    runId,
                    saved.getTargetDate(),
                    saved.getAvgTempC(),
                    saved.getPrecipitationMm(),
                    saved.getIsRain(),
                    durationMs);
        } catch (Exception ex) {
            long durationMs = Duration.between(startedAt, Instant.now()).toMillis();
            log.error("날씨 컨텍스트 적재 실패: runId={}, durationMs={}, message={}", runId, durationMs, ex.getMessage(), ex);
        } finally {
            runLock.unlock();
        }
    }
}
