package com.errorzero.conv.service.holiday;

import java.time.LocalDate;

public interface HolidayApiClient {
    boolean isPublicHoliday(LocalDate date);
}
