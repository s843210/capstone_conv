package com.errorzero.conv.repository;

import com.errorzero.conv.domain.Product;
import com.querydsl.jpa.impl.JPAQueryFactory;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Repository;

import java.util.List;

import static com.errorzero.conv.domain.QProduct.product;

@Repository
@RequiredArgsConstructor
public class ProductRepositoryCustomImpl implements ProductRepositoryCustom {

    private static final String SORT_STOCK_DESC = "stock_desc";

    private final JPAQueryFactory queryFactory;

    @Override
    public long countActiveProducts() {
        Long count = queryFactory
                .select(product.count())
                .from(product)
                .where(product.isActive.isTrue())
                .fetchOne();
        return count != null ? count : 0L;
    }

    @Override
    public long countLowStockProducts(int threshold) {
        Long count = queryFactory
                .select(product.count())
                .from(product)
                .where(
                        product.isActive.isTrue(),
                        product.currentStock.lt(threshold)
                )
                .fetchOne();
        return count != null ? count : 0L;
    }

    @Override
    public Page<Product> findInventoryPage(String keyword, String category, String sort, Pageable pageable) {
        var where = new com.querydsl.core.BooleanBuilder();
        where.and(product.isActive.isTrue());

        if (keyword != null && !keyword.isBlank()) {
            String trimmedKeyword = keyword.trim();
            where.and(
                    product.name.containsIgnoreCase(trimmedKeyword)
                            .or(product.pluCode.containsIgnoreCase(trimmedKeyword))
            );
        }

        if (category != null && !category.isBlank()) {
            where.and(product.category.eq(category.trim()));
        }

        var orderSpecifier = SORT_STOCK_DESC.equalsIgnoreCase(sort)
                ? product.currentStock.desc()
                : product.currentStock.asc();

        List<Product> content = queryFactory
                .selectFrom(product)
                .where(where)
                .orderBy(orderSpecifier, product.id.asc())
                .offset(pageable.getOffset())
                .limit(pageable.getPageSize())
                .fetch();

        Long total = queryFactory
                .select(product.count())
                .from(product)
                .where(where)
                .fetchOne();

        return new PageImpl<>(content, pageable, total != null ? total : 0L);
    }

    @Override
    public List<String> findActiveCategories() {
        return queryFactory
                .select(product.category)
                .distinct()
                .from(product)
                .where(
                        product.isActive.isTrue(),
                        product.category.isNotNull(),
                        product.category.ne("")
                )
                .orderBy(product.category.asc())
                .fetch();
    }
}
