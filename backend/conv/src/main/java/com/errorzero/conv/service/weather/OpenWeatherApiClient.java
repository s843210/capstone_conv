package com.errorzero.conv.service.weather;

import com.errorzero.conv.config.WeatherProperties;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class OpenWeatherApiClient implements WeatherApiClient {

    private static final DateTimeFormatter DATE_TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final RestClient weatherRestClient;
    private final WeatherProperties weatherProperties;

    @Override
    public WeatherSnapshot fetchDailyWeather(LocalDate targetDate) {
        String apiKey = weatherProperties.getApiKey();
        if (apiKey == null || apiKey.isBlank()) {
            throw new IllegalStateException("WEATHER_API_KEY가 비어있습니다. .env에 키를 설정하세요.");
        }

        Map<String, Object> response = weatherRestClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path(weatherProperties.getForecastPath())
                        .queryParam("lat", weatherProperties.getLatitude())
                        .queryParam("lon", weatherProperties.getLongitude())
                        .queryParam("appid", apiKey)
                        .queryParam("units", "metric")
                        .build())
                .retrieve()
                .body(Map.class);

        if (response == null) {
            throw new IllegalStateException("날씨 API 응답이 비어있습니다.");
        }

        Object listObj = response.get("list");
        if (!(listObj instanceof List<?> list) || list.isEmpty()) {
            throw new IllegalStateException("날씨 API list 데이터가 없습니다.");
        }

        double tempSum = 0.0;
        int tempCount = 0;
        double precipitationSum = 0.0;

        for (Object item : list) {
            if (!(item instanceof Map<?, ?> rawEntry)) {
                continue;
            }

            Map<String, Object> entry = castMap(rawEntry);
            LocalDate entryDate = extractDate(entry, weatherProperties.getScheduleZone());
            if (!targetDate.equals(entryDate)) {
                continue;
            }

            Double temp = extractNestedDouble(entry, "main", "temp");
            if (temp != null) {
                tempSum += temp;
                tempCount++;
            }

            precipitationSum += extractPrecipitation(entry);
        }

        if (tempCount == 0) {
            throw new IllegalStateException("요청 날짜(" + targetDate + ")의 날씨 데이터가 없습니다.");
        }

        double avgTemp = tempSum / tempCount;
        short isRain = precipitationSum > 0.0 ? (short) 1 : (short) 0;

        return new WeatherSnapshot(avgTemp, precipitationSum, isRain);
    }

    private LocalDate extractDate(Map<String, Object> entry, String zone) {
        Object dtTxt = entry.get("dt_txt");
        if (dtTxt instanceof String dtTxtStr) {
            LocalDateTime dateTime = LocalDateTime.parse(dtTxtStr, DATE_TIME_FORMATTER);
            return dateTime.toLocalDate();
        }

        Object dt = entry.get("dt");
        if (dt instanceof Number epochSec) {
            return Instant.ofEpochSecond(epochSec.longValue())
                    .atZone(ZoneId.of(zone))
                    .toLocalDate();
        }

        throw new IllegalStateException("날씨 데이터에 날짜 필드(dt/dt_txt)가 없습니다.");
    }

    private Double extractNestedDouble(Map<String, Object> source, String parentKey, String childKey) {
        Map<String, Object> parentMap = getMap(source, parentKey);
        if (parentMap == null) {
            return null;
        }

        Object value = parentMap.get(childKey);
        return toDouble(value);
    }

    private double extractPrecipitation(Map<String, Object> entry) {
        double rain = readMm(entry, "rain");
        double snow = readMm(entry, "snow");
        return Math.max(0.0, rain + snow);
    }

    private double readMm(Map<String, Object> source, String key) {
        Map<String, Object> mmMap = getMap(source, key);
        if (mmMap == null) {
            return 0.0;
        }
        Double value = toDouble(mmMap.get("3h"));
        return value == null ? 0.0 : value;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> getMap(Map<String, Object> source, String key) {
        Object value = source.get(key);
        if (!(value instanceof Map<?, ?> raw)) {
            return null;
        }
        return (Map<String, Object>) raw;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> castMap(Map<?, ?> raw) {
        return (Map<String, Object>) raw;
    }

    private Double toDouble(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value instanceof String valueStr) {
            try {
                return Double.parseDouble(valueStr);
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }
}
