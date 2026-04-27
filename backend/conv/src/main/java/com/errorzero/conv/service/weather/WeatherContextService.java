package com.errorzero.conv.service.weather;

import com.errorzero.conv.config.WeatherProperties;
import com.errorzero.conv.domain.DailyContext;
import com.errorzero.conv.repository.DailyContextRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;

@Slf4j
@Service
@RequiredArgsConstructor
public class WeatherContextService {

    private final DailyContextRepository dailyContextRepository;
    private final WeatherApiClient weatherApiClient;
    private final WeatherProperties weatherProperties;

    @Transactional(readOnly = true)
    public WeatherSnapshot fetchWeatherWithRetry(LocalDate targetDate) {
        int maxAttempts = Math.max(weatherProperties.getRetryCount(), 1);
        long backoffMs = Math.max(weatherProperties.getRetryBackoffMillis(), 100L);

        RuntimeException lastException = null;

        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                return weatherApiClient.fetchDailyWeather(targetDate);
            } catch (RuntimeException ex) {
                lastException = ex;
                log.warn("날씨 조회 실패: targetDate={}, attempt={}/{}, reason={}",
                        targetDate, attempt, maxAttempts, ex.getMessage());

                if (attempt < maxAttempts) {
                    sleep(backoffMs * (1L << (attempt - 1)));
                }
            }
        }

        throw new IllegalStateException("날씨 API 조회 재시도 실패: targetDate=" + targetDate, lastException);
    }

    @Transactional
    public DailyContext upsertWeatherContext(LocalDate targetDate) {
        if (!weatherProperties.isEnabled()) {
            throw new IllegalStateException("날씨 수집이 비활성화되어 있습니다. WEATHER_ENABLED=true로 설정하세요.");
        }

        WeatherSnapshot snapshot = fetchWeatherWithRetry(targetDate);

        DailyContext context = dailyContextRepository.findById(targetDate)
                .orElseGet(() -> DailyContext.createDefault(targetDate));

        context.setAvgTempC(snapshot.avgTempC());
        context.setPrecipitationMm(Math.max(0.0, snapshot.precipitationMm()));
        context.setIsRain(snapshot.isRain() == 1 ? (short) 1 : (short) 0);

        if (context.getIsHoliday() == null) {
            context.setIsHoliday((short) 0);
        }
        if (context.getAcademicEvent() == null) {
            context.setAcademicEvent(0);
        }
        if (context.getBuildingHeadcount() == null) {
            context.setBuildingHeadcount(0);
        }

        return dailyContextRepository.save(context);
    }

    @Transactional
    public DailyContext upsertWeatherContext(LocalDate targetDate, WeatherSnapshot snapshot) {
        DailyContext context = dailyContextRepository.findById(targetDate)
                .orElseGet(() -> DailyContext.createDefault(targetDate));

        context.setAvgTempC(snapshot.avgTempC());
        context.setPrecipitationMm(Math.max(0.0, snapshot.precipitationMm()));
        context.setIsRain(snapshot.isRain() == 1 ? (short) 1 : (short) 0);

        if (context.getIsHoliday() == null) {
            context.setIsHoliday((short) 0);
        }
        if (context.getAcademicEvent() == null) {
            context.setAcademicEvent(0);
        }
        if (context.getBuildingHeadcount() == null) {
            context.setBuildingHeadcount(0);
        }

        return dailyContextRepository.save(context);
    }

    private void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("날씨 조회 재시도 대기 중 인터럽트 발생", e);
        }
    }
}
