package com.errorzero.conv.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;

import java.util.List;

@Getter
@Builder
@AllArgsConstructor
public class InventoryResponseDto {
    private List<ItemDto> items;
    private boolean hasNext;
    private int currentPage;
    private long totalElements;

    @Getter
    @Builder
    @AllArgsConstructor
    public static class ItemDto {
        private String pluCode;
        private String name;
        private int currentStock;
        private int recommendedStock;
    }
}
