package com.errorzero.conv.repository;

public interface TopSalesProductProjection {
    String getPluCode();

    String getName();

    Integer getCurrentStock();

    Integer getSalesQty();
}
